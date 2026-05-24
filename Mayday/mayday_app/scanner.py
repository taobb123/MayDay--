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

def artist_identity_key(artist: str) -> str:
    """用于关联同一歌手的不同写法（如简繁体）"""
    pinyin, _ = _generate_pinyin_fields(artist)
    if pinyin:
        return pinyin.lower()
    return (artist or '').strip().lower()


def _generate_pinyin_fields(artist: str) -> tuple[str, str]:
    """生成歌手的拼音和首字母"""
    try:
        from pypinyin import lazy_pinyin, Style
        
        if not artist:
            return '', ''
        
        # 生成拼音
        pinyin_list = lazy_pinyin(artist, style=Style.NORMAL)
        pinyin = ''.join(pinyin_list)
        
        # 获取首字母
        if pinyin:
            initial = pinyin[0].upper()
        else:
            # 如果是英文，直接取首字母
            initial = artist[0].upper() if artist else ''
        
        return pinyin, initial
    except ImportError:
        # 如果pypinyin未安装，返回空字符串
        return '', ''

if TYPE_CHECKING:
    from .interfaces import SongInterface


class MusicScanner(MusicScannerInterface):
    """音乐扫描器实现 - 使用委托模式处理不同文件格式"""
    
    # 支持的音频格式
    SUPPORTED_FORMATS = {'.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg'}
    
    # 允许创建专辑的目录（只有从此目录扫描的文件才会创建新专辑）
    ALLOWED_ALBUM_DIRECTORY = r'D:\Music\五月天'
    
    def __init__(self, directory_path: Optional[str] = None):
        self.directory_path = directory_path or settings.MUSIC_DIRECTORY
        self._scan_root: Optional[str] = None
        self._path_index: Optional[Dict[str, int]] = None
    
    def _default_artist(self) -> str:
        """方案 A：元信息无艺术家时，使用扫描根目录的文件夹名"""
        root = self._scan_root or self.directory_path
        if root:
            name = Path(root).name.strip()
            if name:
                return name
        return '未知艺术家'
    
    def _resolve_artist(self, tag_artist: Optional[str]) -> str:
        """优先使用元信息艺术家，否则使用扫描根目录名"""
        if tag_artist and str(tag_artist).strip():
            return str(tag_artist).strip()
        return self._default_artist()
    
    def _canonical_artist(self, tag_artist: Optional[str]) -> str:
        """入库用艺术家名：与扫描根目录仅简繁差异时统一为文件夹名"""
        resolved = self._resolve_artist(tag_artist)
        folder = self._default_artist()
        if folder == '未知艺术家':
            return resolved
        if artist_identity_key(resolved) == artist_identity_key(folder):
            return folder
        return resolved
    
    def _path_variants(self, file_path: Path) -> List[str]:
        """生成用于匹配的路径变体（resolve / absolute）"""
        variants: List[str] = []
        for getter in (lambda: file_path.resolve(), lambda: file_path.absolute()):
            try:
                variants.append(str(getter()))
            except (OSError, RuntimeError):
                pass
        return list(dict.fromkeys(variants))
    
    def _build_path_index(self) -> None:
        """扫描前构建路径索引，加速按路径查找"""
        self._path_index = {}
        for row in Song.objects.exclude(original_path='').values('id', 'original_path'):
            path = row['original_path']
            self._path_index[path] = row['id']
            if os.name == 'nt':
                self._path_index[os.path.normcase(path)] = row['id']
    
    def _find_song_by_path(self, path_variants: List[str]) -> Optional[Song]:
        """仅按文件路径查找已有歌曲（避免标题+艺术家误匹配其它文件）"""
        for path_str in path_variants:
            song = Song.objects.filter(original_path=path_str).first()
            if song:
                return song
            if self._path_index is not None:
                song_id = self._path_index.get(path_str)
                if song_id is None and os.name == 'nt':
                    song_id = self._path_index.get(os.path.normcase(path_str))
                if song_id is not None:
                    return Song.objects.filter(pk=song_id).first()
        return None
    
    def scan_directory(self, directory_path: str) -> List[Song]:
        """扫描目录并返回歌曲列表"""
        songs = []
        path = Path(directory_path)
        
        if not path.exists():
            return songs
        
        self._scan_root = directory_path
        self._build_path_index()
        try:
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
        finally:
            self._scan_root = None
            self._path_index = None
        
        return songs
    
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """提取音频文件元数据 - 委托给mutagen库"""
        try:
            audio_file = MutagenFile(file_path)
            if audio_file is None:
                return {}
            
            tag_artist = (
                self._get_tag(audio_file, 'TPE1')
                or self._get_tag(audio_file, 'ARTIST')
                or self._get_tag(audio_file, 'artist')
            )
            metadata = {
                'title': (
                    self._get_tag(audio_file, 'TIT2')
                    or self._get_tag(audio_file, 'TITLE')
                    or self._get_tag(audio_file, 'title')
                    or Path(file_path).stem
                ),
                'artist': self._canonical_artist(tag_artist),
                'album': (
                    self._get_tag(audio_file, 'TALB')
                    or self._get_tag(audio_file, 'ALBUM')
                    or self._get_tag(audio_file, 'album')
                ),
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
                'artist': self._canonical_artist(None),
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
            # 检查文件路径是否在允许创建专辑的目录下
            try:
                file_path_resolved = file_path.resolve()
                allowed_dir = Path(self.ALLOWED_ALBUM_DIRECTORY).resolve()
                is_in_allowed_directory = str(file_path_resolved).startswith(str(allowed_dir))
            except (OSError, RuntimeError):
                # 如果路径解析失败，使用绝对路径比较
                try:
                    file_path_abs = file_path.absolute()
                    allowed_dir_abs = Path(self.ALLOWED_ALBUM_DIRECTORY).absolute()
                    is_in_allowed_directory = str(file_path_abs).startswith(str(allowed_dir_abs))
                except Exception:
                    # 如果都失败，默认不允许创建专辑
                    is_in_allowed_directory = False
            
            # 查找已存在的专辑（禁止创建新专辑）
            # 只关联到数据库中已存在的专辑，不会创建新专辑
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
                    # 注意：禁止创建新专辑
                    # 如果专辑不存在，album保持为None，歌曲将不关联任何专辑
            
            path_variants = self._path_variants(file_path)
            original_path_str = path_variants[0] if path_variants else str(file_path)
            
            # 仅按路径匹配已有记录，避免标题+艺术家误关联到其它文件
            song = self._find_song_by_path(path_variants)
            
            artist = metadata.get('artist') or self._canonical_artist(None)
            # 生成拼音字段
            artist_pinyin, artist_initial = _generate_pinyin_fields(artist)
            
            if song:
                # 更新现有记录
                song.title = metadata.get('title', file_path.stem)
                song.artist = artist
                song.artist_pinyin = artist_pinyin
                song.artist_initial = artist_initial
                song.album = album
                song.duration = metadata.get('duration')
                song.track_number = metadata.get('track_number')
                song.original_path = original_path_str  # 更新路径
                song.save()
                if self._path_index is not None:
                    self._path_index[original_path_str] = song.pk
                    if os.name == 'nt':
                        self._path_index[os.path.normcase(original_path_str)] = song.pk
            else:
                # 创建新记录
                song = Song.objects.create(
                    title=metadata.get('title', file_path.stem),
                    artist=artist,
                    artist_pinyin=artist_pinyin,
                    artist_initial=artist_initial,
                    album=album,
                    duration=metadata.get('duration'),
                    track_number=metadata.get('track_number'),
                    original_path=original_path_str,
                )
                if self._path_index is not None:
                    self._path_index[original_path_str] = song.pk
                    if os.name == 'nt':
                        self._path_index[os.path.normcase(original_path_str)] = song.pk
            
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

