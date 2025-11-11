"""
文件扫描模块 - 使用代理模式和委托模式
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from mutagen import File as MutagenFile
from mutagen.id3 import ID3NoHeaderError
from django.conf import settings
from .interfaces import MusicScannerInterface
from .models import Song, Album

if TYPE_CHECKING:
    from .interfaces import SongInterface


class MusicScanner(MusicScannerInterface):
    """音乐扫描器实现 - 使用委托模式处理不同文件格式"""
    
    # 支持的音频格式
    SUPPORTED_FORMATS = {'.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg'}
    
    def __init__(self, directory_path: Optional[str] = None):
        self.directory_path = directory_path or settings.MUSIC_DIRECTORY
    
    def scan_directory(self, directory_path: str) -> List[Song]:
        """扫描目录并返回歌曲列表"""
        songs = []
        path = Path(directory_path)
        
        if not path.exists():
            return songs
        
        # 递归扫描所有音频文件
        for file_path in path.rglob('*'):
            # 确保是文件而不是目录
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_FORMATS:
                try:
                    metadata = self.extract_metadata(str(file_path))
                    if metadata:
                        # 创建或更新歌曲记录
                        song = self._create_or_update_song(file_path, metadata)
                        if song:
                            songs.append(song)
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
        
        return songs
    
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """提取音频文件元数据 - 委托给mutagen库"""
        try:
            audio_file = MutagenFile(file_path)
            if audio_file is None:
                return {}
            
            metadata = {
                'title': self._get_tag(audio_file, 'TIT2') or self._get_tag(audio_file, 'TITLE') or Path(file_path).stem,
                'artist': self._get_tag(audio_file, 'TPE1') or self._get_tag(audio_file, 'ARTIST') or '五月天',
                'album': self._get_tag(audio_file, 'TALB') or self._get_tag(audio_file, 'ALBUM'),
                'track_number': self._get_tag(audio_file, 'TRCK') or self._get_tag(audio_file, 'TRACKNUMBER'),
                'duration': audio_file.info.length if hasattr(audio_file.info, 'length') else None,
            }
            
            # 清理track_number
            if metadata['track_number']:
                try:
                    # 处理 "1/10" 格式
                    track_num = str(metadata['track_number']).split('/')[0]
                    metadata['track_number'] = int(track_num)
                except (ValueError, AttributeError):
                    metadata['track_number'] = None
            
            return metadata
        except (ID3NoHeaderError, Exception) as e:
            # 记录错误但不中断扫描（使用警告级别，因为这不是严重错误）
            error_msg = str(e)
            if 'sync' in error_msg.lower() or 'mpeg' in error_msg.lower():
                print(f"⚠️ 无法提取元数据（文件格式可能不标准）: {Path(file_path).name}")
            else:
                print(f"⚠️ 元数据提取失败: {Path(file_path).name} - {error_msg}")
            
            # 返回基本元数据，确保文件仍然可以被添加到数据库
            return {
                'title': Path(file_path).stem,
                'artist': '五月天',
                'album': None,
                'track_number': None,
                'duration': None,
            }
    
    def _get_tag(self, audio_file, tag_name: str) -> Optional[str]:
        """获取标签值 - 委托方法"""
        try:
            if tag_name in audio_file:
                value = audio_file[tag_name][0]
                return str(value) if value else None
        except (KeyError, IndexError, AttributeError):
            pass
        return None
    
    def _create_or_update_song(self, file_path: Path, metadata: Dict[str, Any]) -> Optional[Song]:
        """创建或更新歌曲记录"""
        try:
            # 查找或创建专辑（规范化名称，避免重复）
            album = None
            if metadata.get('album'):
                # 规范化专辑名称：去除首尾空格
                album_name = metadata['album'].strip()
                if album_name:
                    # 先尝试精确匹配
                    album = Album.objects.filter(name=album_name).first()
                    # 如果没有找到，尝试模糊匹配（去除所有空格后比较）
                    # 使用数据库查询优化，避免加载所有专辑到内存
                    if not album:
                        normalized_name = album_name.replace(' ', '').replace('　', '')
                        # 获取所有专辑并检查规范化后的名称
                        albums = Album.objects.all().only('id', 'name')
                        for existing_album in albums:
                            normalized_existing = existing_album.name.replace(' ', '').replace('　', '')
                            if normalized_existing == normalized_name:
                                album = existing_album
                                break
                    # 如果还是没找到，创建新专辑
                    if not album:
                        album, _ = Album.objects.get_or_create(
                            name=album_name,
                            defaults={'release_date': '2000-01-01'}  # 默认日期，后续可手动更新
                        )
            
            # 规范化文件路径（统一路径格式）
            try:
                # 使用绝对路径，统一路径格式
                original_path_str = str(file_path.resolve())
            except (OSError, RuntimeError):
                # 如果无法解析路径，使用原始路径
                original_path_str = str(file_path.absolute())
            
            # 首先尝试用 original_path 匹配
            song = Song.objects.filter(original_path=original_path_str).first()
            
            # 如果找不到，尝试用标题、艺术家和专辑匹配（避免重复创建）
            if not song:
                title = metadata.get('title', file_path.stem)
                artist = metadata.get('artist', '五月天')
                
                # 查找相同标题、艺术家和专辑的歌曲
                query = Song.objects.filter(
                    title=title,
                    artist=artist
                )
                if album:
                    query = query.filter(album=album)
                else:
                    query = query.filter(album__isnull=True)
                
                song = query.first()
            
            if song:
                # 更新现有记录
                song.title = metadata.get('title', file_path.stem)
                song.artist = metadata.get('artist', '五月天')
                song.album = album
                song.duration = metadata.get('duration')
                song.track_number = metadata.get('track_number')
                song.original_path = original_path_str  # 更新路径
                song.save()
            else:
                # 创建新记录
                song = Song.objects.create(
                    title=metadata.get('title', file_path.stem),
                    artist=metadata.get('artist', '五月天'),
                    album=album,
                    duration=metadata.get('duration'),
                    track_number=metadata.get('track_number'),
                    original_path=original_path_str,
                )
            
            return song
        except Exception as e:
            print(f"Error creating song record: {e}")
            return None


class MusicScannerProxy:
    """音乐扫描器代理 - 实现代理模式，添加缓存和日志功能"""
    
    def __init__(self, scanner: MusicScannerInterface):
        self._scanner = scanner
        self._cache: Dict[str, List[Song]] = {}
    
    def scan_directory(self, directory_path: str, use_cache: bool = True) -> List[Song]:
        """扫描目录（带缓存）"""
        if use_cache and directory_path in self._cache:
            return self._cache[directory_path]
        
        songs = self._scanner.scan_directory(directory_path)
        
        if use_cache:
            self._cache[directory_path] = songs
        
        return songs
    
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """提取元数据（委托给真实对象）"""
        return self._scanner.extract_metadata(file_path)
    
    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()

