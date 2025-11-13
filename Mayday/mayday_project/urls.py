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
    # 重定向 /accounts/login/ 到 /login/
    path('accounts/login/', RedirectView.as_view(url='/login/', permanent=False, query_string=True)),
    path('api/', include('mayday_app.urls')),
    path('', include('mayday_app.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

