"""
前端不再要求登录：产品页始终使用本机唯一账号。
/admin/ 不处理，管理后台仍走 Django 管理员登录，且不会改写前台身份。
"""
from django.contrib.auth import login
from django.db.utils import OperationalError, ProgrammingError

from .identity import (
    AUTH_BACKEND,
    attach_product_user,
    get_product_user,
    is_admin_session_user,
)

SKIP_PREFIXES = ('/admin/', '/static/', '/media/')


class GuestSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or '/'
        if path.startswith(SKIP_PREFIXES):
            return self.get_response(request)
        try:
            product_user = get_product_user()
        except (OperationalError, ProgrammingError):
            return self.get_response(request)

        if is_admin_session_user(request.user):
            # 管理员已登录后台：前台仍用本机账号，但不 login() 以免踢出后台
            attach_product_user(request, product_user)
            return self.get_response(request)

        current = getattr(request, 'user', None)
        if (
            not getattr(current, 'is_authenticated', False)
            or getattr(current, 'pk', None) != product_user.pk
        ):
            login(request, product_user, backend=AUTH_BACKEND)
        return self.get_response(request)
