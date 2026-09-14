"""
前端不再要求登录：为产品页自动挂上本机身份，歌单/收藏/会员可直接用。
/admin/ 不处理，管理后台仍走 Django 管理员登录。
"""
from django.contrib.auth import get_user_model, login
from django.db.utils import OperationalError, ProgrammingError

LOCAL_USERNAME = 'mayday_local'
AUTH_BACKEND = 'django.contrib.auth.backends.ModelBackend'
SKIP_PREFIXES = ('/admin/', '/static/', '/media/')


def get_product_user():
    """本机固定访客账号，歌单/收藏/会员都记在它上面。"""
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=LOCAL_USERNAME,
        defaults={'email': ''},
    )
    if created or user.has_usable_password():
        user.set_unusable_password()
        user.save(update_fields=['password'])
    return user


class GuestSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or '/'
        if path.startswith(SKIP_PREFIXES):
            return self.get_response(request)
        if getattr(request.user, 'is_authenticated', False):
            return self.get_response(request)
        try:
            user = get_product_user()
        except (OperationalError, ProgrammingError):
            return self.get_response(request)
        login(request, user, backend=AUTH_BACKEND)
        return self.get_response(request)
