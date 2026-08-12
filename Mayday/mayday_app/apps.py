from django.apps import AppConfig


class MaydayAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mayday_app'
    verbose_name = '五月天音乐收藏系统'

    def ready(self):
        # 注册 User → MembershipProfile 信号
        from . import membership  # noqa: F401

