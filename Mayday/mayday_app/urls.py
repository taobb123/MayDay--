"""
URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'albums', views.AlbumViewSet)
router.register(r'songs', views.SongViewSet)
router.register(r'tours', views.TourViewSet)
router.register(r'quotes', views.QuoteViewSet)
router.register(r'images', views.ImageViewSet)

urlpatterns = [
    # API路由
    path('api/', include(router.urls)),
    path('api/scan/', views.ScanView.as_view(), name='scan'),
    path('api/timeline/', views.TimelineView.as_view(), name='timeline'),
    
    # 页面路由
    path('', views.index, name='index'),
    path('album/<int:album_id>/', views.album_detail, name='album_detail'),
    path('play/<int:song_id>/', views.play_song, name='play_song'),
]

