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
router.register(r'playlists', views.PlaylistViewSet)

urlpatterns = [
    # API路由
    path('api/', include(router.urls)),
    path('api/scan/', views.ScanView.as_view(), name='scan'),
    path('api/timeline/', views.TimelineView.as_view(), name='timeline'),
    path('api/search/', views.SearchView.as_view(), name='search'),
    
    # 用户认证路由
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # 歌单页面路由
    path('playlists/', views.playlist_list_view, name='playlist_list'),
    path('playlist/<int:playlist_id>/', views.playlist_detail_view, name='playlist_detail'),
    
    # 页面路由
    path('', views.index, name='index'),
    path('album/<int:album_id>/', views.album_detail, name='album_detail'),
    path('play/<int:song_id>/', views.play_song, name='play_song'),
]

