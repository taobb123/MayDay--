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
    # 歌单API路由（使用JsonResponse确保返回JSON）- 必须在router之前，避免路由冲突
    # 简单函数视图API（优先匹配）
    path('api/playlists/list/', views.get_playlists_api, name='get_playlists_api'),
    path('api/playlists/create/', views.create_playlist_api, name='create_playlist_api'),
    path('api/playlists/<int:playlist_id>/update/', views.update_playlist_api, name='update_playlist_api'),
    path('api/playlists/<int:playlist_id>/delete/', views.delete_playlist_api, name='delete_playlist_api'),
    path('api/playlists/<int:playlist_id>/add_song/', views.add_song_to_playlist_api, name='add_song_to_playlist_api'),
    path('api/playlists/<int:playlist_id>/songs/<int:song_id>/', views.remove_song_from_playlist_api, name='remove_song_from_playlist_api'),
    path('api/favorites/list/', views.favorites_list_api, name='favorites_list_api'),
    path('api/favorites/ids/', views.favorite_ids_api, name='favorite_ids_api'),
    path('api/favorites/toggle/', views.favorite_toggle_api, name='favorite_toggle_api'),
    
    # API路由（DRF ViewSet，放在后面避免冲突）
    path('api/', include(router.urls)),
    path('api/scan/', views.ScanView.as_view(), name='scan'),
    path('api/search/', views.SearchView.as_view(), name='search'),
    path('api/search/artists/', views.ArtistSearchView.as_view(), name='artist_search'),
    path('api/search/artist-songs/', views.ArtistSongsView.as_view(), name='artist_songs'),
    path('api/artists/by-initial/', views.ArtistsByInitialView.as_view(), name='artists_by_initial'),
    path('api/membership/status/', views.membership_status_api, name='membership_status_api'),
    path('api/membership/upgrade/', views.membership_upgrade_api, name='membership_upgrade_api'),
    path('api/payments/checkout/', views.payments_checkout_api, name='payments_checkout_api'),
    path('api/payments/webhook/stripe/', views.payments_stripe_webhook, name='payments_stripe_webhook'),
    
    # 用户认证路由
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # 歌单页面路由
    path('playlists/', views.playlist_list_view, name='playlist_list'),
    path('playlist/<int:playlist_id>/', views.playlist_detail_view, name='playlist_detail'),
    path('random-playlist/', views.random_playlist_view, name='random_playlist'),
    path('membership/', views.membership_view, name='membership'),
    path('membership/success/', views.membership_success_view, name='membership_success'),
    path('favorites/', views.favorites_view, name='favorites'),
    
    # 页面路由
    path('', views.index, name='index'),
    path('album/<int:album_id>/', views.album_detail, name='album_detail'),
    path('play/<int:song_id>/', views.play_song, name='play_song'),
]

