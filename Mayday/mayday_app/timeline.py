"""
时间线模块 - 实现时间线仓库接口
使用组合模式整合不同类型的时间线项目
"""
from __future__ import annotations
from typing import List, Dict, Any, TYPE_CHECKING
from datetime import datetime
from django.db.models import Q
from .interfaces import TimelineRepositoryInterface
from .models import Album, Tour, Quote, Image

if TYPE_CHECKING:
    from .interfaces import TimeTunnelItem


class TimelineRepository(TimelineRepositoryInterface):
    """时间线仓库实现 - 使用组合模式整合不同类型项目"""
    
    def __init__(self):
        # 使用组合而非继承：组合不同类型的模型
        self._item_creators = {
            'album': Album,
            'tour': Tour,
            'quote': Quote,
            'image': Image,
        }
    
    def add_item(self, item: Any) -> None:
        """添加时间线项目"""
        # 如果item已经是模型实例，直接保存
        if hasattr(item, 'save'):
            item.save()
        # 否则根据类型创建新实例
        else:
            item_type = item.get_type()
            if item_type in self._item_creators:
                # 这里可以根据item的内容创建新实例
                pass
    
    def get_items_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Any]:
        """根据日期范围获取项目 - 组合所有类型"""
        items: List[Any] = []
        
        # 组合查询所有类型
        albums = Album.objects.filter(release_date__range=[start_date.date(), end_date.date()])
        items.extend(list(albums))
        
        tours = Tour.objects.filter(
            Q(start_date__lte=end_date.date()) & 
            (Q(end_date__gte=start_date.date()) | Q(end_date__isnull=True))
        )
        items.extend(list(tours))
        
        quotes = Quote.objects.filter(date__range=[start_date.date(), end_date.date()])
        items.extend(list(quotes))
        
        images = Image.objects.filter(date__range=[start_date.date(), end_date.date()])
        items.extend(list(images))
        
        # 按日期排序
        items.sort(key=lambda x: x.get_date(), reverse=True)
        
        return items
    
    def get_all_items(self) -> List[Any]:
        """获取所有项目 - 组合所有类型"""
        items: List[Any] = []
        
        items.extend(list(Album.objects.all()))
        items.extend(list(Tour.objects.all()))
        items.extend(list(Quote.objects.all()))
        items.extend(list(Image.objects.all()))
        
        # 按日期排序
        items.sort(key=lambda x: x.get_date(), reverse=True)
        
        return items
    
    def get_items_by_type(self, item_type: str) -> List[Any]:
        """根据类型获取项目"""
        if item_type == 'album':
            return list(Album.objects.all())
        elif item_type == 'tour':
            return list(Tour.objects.all())
        elif item_type == 'quote':
            return list(Quote.objects.all())
        elif item_type == 'image':
            return list(Image.objects.all())
        else:
            return []
    
    def get_timeline_data(self) -> List[Dict[str, Any]]:
        """获取格式化的时间线数据"""
        items = self.get_all_items()
        timeline_data = []
        
        for item in items:
            timeline_data.append({
                'type': item.get_type(),
                'date': item.get_date().isoformat(),
                'title': item.get_title(),
                'content': item.get_content(),
            })
        
        return timeline_data

