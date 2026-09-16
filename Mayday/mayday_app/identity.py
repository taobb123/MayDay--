"""
产品只保留一个本机账号：歌单 / 收藏 / 会员都记在它上面。
管理后台账号只用于 /admin/，不参与前台身份。
"""
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.utils import timezone

LOCAL_USERNAME = 'mayday_local'
AUTH_BACKEND = 'django.contrib.auth.backends.ModelBackend'


def get_product_user():
    """本机固定账号。不可登录前台，也不是管理员。"""
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=LOCAL_USERNAME,
        defaults={'email': '', 'is_staff': False, 'is_superuser': False, 'is_active': True},
    )
    changed = []
    if created or user.has_usable_password():
        user.set_unusable_password()
        changed.append('password')
    if user.is_staff:
        user.is_staff = False
        changed.append('is_staff')
    if user.is_superuser:
        user.is_superuser = False
        changed.append('is_superuser')
    if not user.is_active:
        user.is_active = True
        changed.append('is_active')
    if changed:
        user.save(update_fields=changed)
    return user


def is_admin_session_user(user):
    return bool(
        getattr(user, 'is_authenticated', False)
        and (getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False))
    )


def attach_product_user(request, product_user):
    """只改当前请求身份，不写进 session，避免冲掉管理后台登录。"""
    request.user = product_user
    request._cached_user = product_user


def unify_product_account():
    """把全部歌单/收藏/订单并到本机账号，并关掉其它前台账号。"""
    from .models import Favorite, MembershipOrder, MembershipProfile, Playlist, PlaylistSong

    target = get_product_user()
    User = get_user_model()

    empty_ids = list(
        Playlist.objects.exclude(user=target)
        .annotate(song_n=Count('songs'))
        .filter(song_n=0)
        .values_list('id', flat=True)
    )
    if empty_ids:
        Playlist.objects.filter(id__in=empty_ids).delete()

    for playlist in list(Playlist.objects.exclude(user=target).prefetch_related('songs')):
        existing = Playlist.objects.filter(user=target, name=playlist.name).first()
        if existing:
            for item in playlist.songs.all():
                PlaylistSong.objects.get_or_create(
                    playlist=existing,
                    song=item.song,
                    defaults={'added_at': item.added_at},
                )
            playlist.delete()
        else:
            playlist.user = target
            playlist.save(update_fields=['user'])

    for fav in list(Favorite.objects.exclude(user=target)):
        Favorite.objects.get_or_create(
            user=target,
            song=fav.song,
            defaults={'created_at': fav.created_at},
        )
        fav.delete()

    MembershipOrder.objects.exclude(user=target).update(user=target)

    now = timezone.now()
    had_active_member = MembershipProfile.objects.filter(
        plan=MembershipProfile.PLAN_MEMBER
    ).exclude(expires_at__lte=now).exists()
    MembershipProfile.objects.exclude(user=target).delete()
    target_mem, _ = MembershipProfile.objects.get_or_create(user=target)
    playlist_count = Playlist.objects.filter(user=target).count()
    if had_active_member or playlist_count > MembershipProfile.FREE_PLAYLIST_LIMIT:
        target_mem.plan = MembershipProfile.PLAN_MEMBER
        target_mem.expires_at = None
        target_mem.save(update_fields=['plan', 'expires_at', 'updated_at'])

    User.objects.exclude(pk=target.pk).filter(
        is_staff=False, is_superuser=False
    ).update(is_active=False)

    return {
        'product_user': target.username,
        'playlists': playlist_count,
        'favorites': Favorite.objects.filter(user=target).count(),
    }
