"""
Django管理后台配置
"""
from django.contrib import admin
from .models import Album, Song, Tour, TourVenue, Quote, Image


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ['name', 'release_date', 'song_count']
    list_filter = ['release_date']
    search_fields = ['name', 'description']
    date_hierarchy = 'release_date'
    
    def get_queryset(self, request):
        """优化查询，预加载歌曲"""
        qs = super().get_queryset(request)
        return qs.prefetch_related('songs')
    
    def song_count(self, obj):
        """获取歌曲数量，使用预加载的数据"""
        if hasattr(obj, '_prefetched_objects_cache') and 'songs' in obj._prefetched_objects_cache:
            return len(obj._prefetched_objects_cache['songs'])
        return obj.songs.count()
    song_count.short_description = '歌曲数量'


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ['title', 'artist', 'album', 'track_number', 'duration']
    list_filter = ['album', 'artist']
    search_fields = ['title', 'artist']
    ordering = ['album', 'track_number']
    
    def get_queryset(self, request):
        """优化查询，预加载专辑"""
        qs = super().get_queryset(request)
        return qs.select_related('album')


@admin.register(Tour)
class TourAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date']
    list_filter = ['start_date']
    search_fields = ['name', 'description']
    date_hierarchy = 'start_date'


@admin.register(TourVenue)
class TourVenueAdmin(admin.ModelAdmin):
    list_display = ['tour', 'name', 'date', 'city']
    list_filter = ['tour', 'date', 'city']
    search_fields = ['name', 'city']


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ['text_preview', 'author', 'date']
    list_filter = ['author', 'date']
    search_fields = ['text', 'author', 'source']
    date_hierarchy = 'date'
    
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = '内容预览'


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ['title', 'date', 'album', 'tour']
    list_filter = ['date', 'album', 'tour']
    search_fields = ['title', 'caption']
    date_hierarchy = 'date'

