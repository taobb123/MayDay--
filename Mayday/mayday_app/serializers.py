"""
序列化器 - 用于API
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Any
from rest_framework import serializers
from .models import Album, Song, Tour, Quote, Image, TourVenue

if TYPE_CHECKING:
    from .interfaces import TimeTunnelItem


class SongSerializer(serializers.ModelSerializer):
    """歌曲序列化器"""
    album_name = serializers.CharField(source='album.name', read_only=True)
    
    class Meta:
        model = Song
        fields = ['id', 'title', 'artist', 'album', 'album_name', 'file_path', 
                  'duration', 'track_number', 'lyrics', 'created_at']


class AlbumSerializer(serializers.ModelSerializer):
    """专辑序列化器"""
    songs = SongSerializer(many=True, read_only=True)
    song_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Album
        fields = ['id', 'name', 'release_date', 'cover_image', 'description', 
                  'songs', 'song_count', 'created_at']
    
    def get_song_count(self, obj):
        """获取歌曲数量，使用预加载的数据"""
        if hasattr(obj, '_prefetched_objects_cache') and 'songs' in obj._prefetched_objects_cache:
            return len(obj._prefetched_objects_cache['songs'])
        return obj.songs.count()


class TourVenueSerializer(serializers.ModelSerializer):
    """巡回演出场地序列化器"""
    class Meta:
        model = TourVenue
        fields = ['id', 'name', 'date', 'city']


class TourSerializer(serializers.ModelSerializer):
    """巡回演出序列化器"""
    venues = TourVenueSerializer(many=True, read_only=True)
    
    class Meta:
        model = Tour
        fields = ['id', 'name', 'start_date', 'end_date', 'description', 
                  'venues', 'created_at']


class QuoteSerializer(serializers.ModelSerializer):
    """言论序列化器"""
    class Meta:
        model = Quote
        fields = ['id', 'text', 'author', 'source', 'date', 'created_at']


class ImageSerializer(serializers.ModelSerializer):
    """图片序列化器"""
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Image
        fields = ['id', 'title', 'image', 'image_url', 'caption', 'date', 
                  'album', 'tour', 'created_at']
    
    def get_image_url(self, obj):
        """获取图片URL"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class TimelineItemSerializer(serializers.Serializer):
    """时间线项目序列化器 - 通用序列化器"""
    type = serializers.CharField()
    date = serializers.DateTimeField()
    title = serializers.CharField()
    content = serializers.DictField()
    
    def to_representation(self, instance: Any):
        """将TimeTunnelItem转换为字典"""
        return {
            'type': instance.get_type(),
            'date': instance.get_date().isoformat(),
            'title': instance.get_title(),
            'content': instance.get_content(),
        }

