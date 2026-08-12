"""
会员骨架：获取/创建资料、权益判断
"""
from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import MembershipProfile, Playlist


def get_or_create_membership(user: User) -> MembershipProfile:
    profile, _ = MembershipProfile.objects.get_or_create(user=user)
    return profile


def membership_status_dict(user: User) -> dict:
    from .payments import payment_mode

    profile = get_or_create_membership(user)
    limit = profile.playlist_limit()
    playlist_count = Playlist.objects.filter(user=user).count()
    pay = payment_mode()
    return {
        'plan': profile.effective_plan(),
        'plan_label': '会员' if profile.is_active_member else '免费',
        'is_member': profile.is_active_member,
        'expires_at': profile.expires_at.isoformat() if profile.expires_at else None,
        'playlist_count': playlist_count,
        'playlist_limit': limit,
        'can_create_playlist': limit is None or playlist_count < limit,
        'demo_note': pay['note'],
        'payment': pay,
        'benefits_preview': [
            '无限歌单（相对免费上限）',
            '高清音质（预告）',
            '高级推荐（预告）',
            '无广告（预告）',
        ],
    }


def mock_upgrade_membership(user: User, days: int = 30) -> MembershipProfile:
    profile = get_or_create_membership(user)
    profile.plan = MembershipProfile.PLAN_MEMBER
    profile.expires_at = timezone.now() + timedelta(days=days)
    profile.save(update_fields=['plan', 'expires_at', 'updated_at'])
    return profile


def assert_can_create_playlist(user: User) -> str | None:
    """若不可创建，返回错误文案；否则 None。"""
    profile = get_or_create_membership(user)
    limit = profile.playlist_limit()
    if limit is None:
        return None
    count = Playlist.objects.filter(user=user).count()
    if count >= limit:
        return f'免费用户最多 {limit} 个歌单，请升级会员后再创建'
    return None


@receiver(post_save, sender=User)
def ensure_membership_profile(sender, instance: User, created: bool, **kwargs):
    if created:
        MembershipProfile.objects.get_or_create(user=instance)
