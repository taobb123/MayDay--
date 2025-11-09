"""
数据模型 - 使用组合而非继承
"""
from __future__ import annotations
from django.db import models
from django.core.validators import FileExtensionValidator
from datetime import datetime
from typing import Optional, List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .interfaces import (
        TimeTunnelItem, AlbumInterface, SongInterface, 
        TourInterface, QuoteInterface, ImageInterface
    )


class Album(models.Model):
    """专辑模型 - 实现AlbumInterface"""
    name = models.CharField(max_length=200, verbose_name='专辑名称')
    release_date = models.DateField(verbose_name='发行日期')
    cover_image = models.ImageField(upload_to='albums/', null=True, blank=True, verbose_name='封面图片')
    description = models.TextField(blank=True, verbose_name='描述')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-release_date']
        verbose_name = '专辑'
        verbose_name_plural = '专辑'
    
    def __str__(self):
        return self.name
    
    # 实现AlbumInterface
    def get_date(self) -> datetime:
        return datetime.combine(self.release_date, datetime.min.time())
    
    def get_title(self) -> str:
        return self.name
    
    def get_content(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'cover_image': self.cover_image.url if self.cover_image else None,
        }
    
    def get_type(self) -> str:
        return 'album'
    
    def get_release_date(self) -> datetime:
        return self.get_date()
    
    def get_songs(self) -> List['Song']:
        return list(self.songs.all())
    
    def get_cover_image(self) -> Optional[str]:
        return self.cover_image.url if self.cover_image else None


class Song(models.Model):
    """歌曲模型 - 实现SongInterface"""
    title = models.CharField(max_length=200, verbose_name='歌曲标题')
    artist = models.CharField(max_length=100, default='五月天', verbose_name='艺术家')
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='songs', null=True, blank=True, verbose_name='专辑')
    file_path = models.FileField(
        upload_to='songs/',
        validators=[FileExtensionValidator(allowed_extensions=['mp3', 'flac', 'wav', 'm4a'])],
        null=True,
        blank=True,
        verbose_name='音频文件（上传）'
    )
    original_path = models.CharField(max_length=500, blank=True, verbose_name='原始文件路径')
    duration = models.FloatField(null=True, blank=True, verbose_name='时长（秒）')
    track_number = models.IntegerField(null=True, blank=True, verbose_name='曲目编号')
    lyrics = models.TextField(blank=True, verbose_name='歌词')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['album', 'track_number', 'title']
        verbose_name = '歌曲'
        verbose_name_plural = '歌曲'
    
    def __str__(self):
        return f"{self.title} - {self.artist}"
    
    # 实现SongInterface
    def get_file_path(self) -> str:
        return self.file_path.path if hasattr(self.file_path, 'path') else str(self.file_path)
    
    def get_title(self) -> str:
        return self.title
    
    def get_artist(self) -> str:
        return self.artist
    
    def get_album(self) -> Optional[str]:
        return self.album.name if self.album else None
    
    def get_duration(self) -> Optional[float]:
        return self.duration


class Tour(models.Model):
    """巡回演出模型 - 实现TourInterface"""
    name = models.CharField(max_length=200, verbose_name='巡回演出名称')
    start_date = models.DateField(verbose_name='开始日期')
    end_date = models.DateField(null=True, blank=True, verbose_name='结束日期')
    description = models.TextField(blank=True, verbose_name='描述')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date']
        verbose_name = '巡回演出'
        verbose_name_plural = '巡回演出'
    
    def __str__(self):
        return self.name
    
    # 实现TourInterface
    def get_date(self) -> datetime:
        return datetime.combine(self.start_date, datetime.min.time())
    
    def get_title(self) -> str:
        return self.name
    
    def get_content(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat() if self.end_date else None,
        }
    
    def get_type(self) -> str:
        return 'tour'
    
    def get_tour_name(self) -> str:
        return self.name
    
    def get_start_date(self) -> datetime:
        return self.get_date()
    
    def get_end_date(self) -> Optional[datetime]:
        return datetime.combine(self.end_date, datetime.min.time()) if self.end_date else None
    
    def get_venues(self) -> List[str]:
        return list(self.venues.values_list('name', flat=True))


class TourVenue(models.Model):
    """巡回演出场地"""
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='venues', verbose_name='巡回演出')
    name = models.CharField(max_length=200, verbose_name='场地名称')
    date = models.DateField(verbose_name='演出日期')
    city = models.CharField(max_length=100, blank=True, verbose_name='城市')
    
    class Meta:
        ordering = ['date']
        verbose_name = '演出场地'
        verbose_name_plural = '演出场地'
    
    def __str__(self):
        return f"{self.tour.name} - {self.name}"


class Quote(models.Model):
    """言论模型 - 实现QuoteInterface"""
    text = models.TextField(verbose_name='言论内容')
    author = models.CharField(max_length=100, blank=True, verbose_name='作者（成员）')
    source = models.CharField(max_length=200, blank=True, verbose_name='来源')
    date = models.DateField(verbose_name='日期')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name = '言论'
        verbose_name_plural = '言论'
    
    def __str__(self):
        return f"{self.text[:50]}..."
    
    # 实现QuoteInterface
    def get_date(self) -> datetime:
        return datetime.combine(self.date, datetime.min.time())
    
    def get_title(self) -> str:
        return f"{self.author}的言论" if self.author else "言论"
    
    def get_content(self) -> Dict[str, Any]:
        return {
            'text': self.text,
            'author': self.author,
            'source': self.source,
        }
    
    def get_type(self) -> str:
        return 'quote'
    
    def get_quote_text(self) -> str:
        return self.text
    
    def get_source(self) -> Optional[str]:
        return self.source if self.source else None
    
    def get_author(self) -> Optional[str]:
        return self.author if self.author else None


class Image(models.Model):
    """图片模型 - 实现ImageInterface"""
    title = models.CharField(max_length=200, verbose_name='标题')
    image = models.ImageField(upload_to='images/', verbose_name='图片')
    caption = models.TextField(blank=True, verbose_name='说明')
    date = models.DateField(verbose_name='日期')
    album = models.ForeignKey(Album, on_delete=models.SET_NULL, null=True, blank=True, related_name='images', verbose_name='关联专辑')
    tour = models.ForeignKey(Tour, on_delete=models.SET_NULL, null=True, blank=True, related_name='images', verbose_name='关联巡回演出')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name = '图片'
        verbose_name_plural = '图片'
    
    def __str__(self):
        return self.title
    
    # 实现ImageInterface
    def get_date(self) -> datetime:
        return datetime.combine(self.date, datetime.min.time())
    
    def get_title(self) -> str:
        return self.title
    
    def get_content(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'caption': self.caption,
            'image_url': self.image.url if self.image else None,
        }
    
    def get_type(self) -> str:
        return 'image'
    
    def get_image_path(self) -> str:
        return self.image.path if hasattr(self.image, 'path') else str(self.image)
    
    def get_caption(self) -> Optional[str]:
        return self.caption if self.caption else None

