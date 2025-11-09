"""
抽象接口定义 - 遵循接口编程而非实现编程
五月天时间隧道抽象类
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from .models import Song


class TimeTunnelItem(ABC):
    """时间隧道项目抽象基类 - 所有时间线项目的基础接口"""
    
    @abstractmethod
    def get_date(self) -> datetime:
        """获取时间线日期"""
        pass
    
    @abstractmethod
    def get_title(self) -> str:
        """获取标题"""
        pass
    
    @abstractmethod
    def get_content(self) -> Dict[str, Any]:
        """获取内容数据"""
        pass
    
    @abstractmethod
    def get_type(self) -> str:
        """获取项目类型（专辑、巡回演出、言论、图片等）"""
        pass


class AlbumInterface(TimeTunnelItem):
    """专辑接口"""
    
    @abstractmethod
    def get_release_date(self) -> datetime:
        """获取发行日期"""
        pass
    
    @abstractmethod
    def get_songs(self) -> List[SongInterface]:
        """获取歌曲列表"""
        pass
    
    @abstractmethod
    def get_cover_image(self) -> Optional[str]:
        """获取封面图片路径"""
        pass


class SongInterface(ABC):
    """歌曲接口"""
    
    @abstractmethod
    def get_file_path(self) -> str:
        """获取文件路径"""
        pass
    
    @abstractmethod
    def get_title(self) -> str:
        """获取歌曲标题"""
        pass
    
    @abstractmethod
    def get_artist(self) -> str:
        """获取艺术家"""
        pass
    
    @abstractmethod
    def get_album(self) -> Optional[str]:
        """获取专辑名"""
        pass
    
    @abstractmethod
    def get_duration(self) -> Optional[float]:
        """获取时长（秒）"""
        pass


class TourInterface(TimeTunnelItem):
    """巡回演出接口"""
    
    @abstractmethod
    def get_tour_name(self) -> str:
        """获取巡回演出名称"""
        pass
    
    @abstractmethod
    def get_start_date(self) -> datetime:
        """获取开始日期"""
        pass
    
    @abstractmethod
    def get_end_date(self) -> Optional[datetime]:
        """获取结束日期"""
        pass
    
    @abstractmethod
    def get_venues(self) -> List[str]:
        """获取演出场地列表"""
        pass


class QuoteInterface(TimeTunnelItem):
    """言论接口"""
    
    @abstractmethod
    def get_quote_text(self) -> str:
        """获取言论文本"""
        pass
    
    @abstractmethod
    def get_source(self) -> Optional[str]:
        """获取来源"""
        pass
    
    @abstractmethod
    def get_author(self) -> Optional[str]:
        """获取作者（成员）"""
        pass


class ImageInterface(TimeTunnelItem):
    """图片接口"""
    
    @abstractmethod
    def get_image_path(self) -> str:
        """获取图片路径"""
        pass
    
    @abstractmethod
    def get_caption(self) -> Optional[str]:
        """获取图片说明"""
        pass


class MusicScannerInterface(ABC):
    """音乐扫描器接口"""
    
    @abstractmethod
    def scan_directory(self, directory_path: str) -> List[Any]:
        """扫描目录并返回歌曲列表"""
        pass
    
    @abstractmethod
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """提取音频文件元数据"""
        pass


class MusicPlayerInterface(ABC):
    """音乐播放器接口"""
    
    @abstractmethod
    def play(self, song: SongInterface) -> None:
        """播放歌曲"""
        pass
    
    @abstractmethod
    def pause(self) -> None:
        """暂停播放"""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """停止播放"""
        pass
    
    @abstractmethod
    def get_current_time(self) -> float:
        """获取当前播放时间"""
        pass
    
    @abstractmethod
    def get_duration(self) -> float:
        """获取总时长"""
        pass


class TimelineRepositoryInterface(ABC):
    """时间线仓库接口"""
    
    @abstractmethod
    def add_item(self, item: Any) -> None:
        """添加时间线项目"""
        pass
    
    @abstractmethod
    def get_items_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Any]:
        """根据日期范围获取项目"""
        pass
    
    @abstractmethod
    def get_all_items(self) -> List[Any]:
        """获取所有项目"""
        pass
    
    @abstractmethod
    def get_items_by_type(self, item_type: str) -> List[Any]:
        """根据类型获取项目"""
        pass

