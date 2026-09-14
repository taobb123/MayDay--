"""
URL configuration for mayday_project project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    # 前端已取消登录，Django 默认登录入口回到首页
    path('accounts/login/', RedirectView.as_view(url='/', permanent=False)),
    path('api/', include('mayday_app.urls')),
    path('', include('mayday_app.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

