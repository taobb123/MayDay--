"""
DRF 分页配置模块
演示不同的分页实现方式
"""
from rest_framework.pagination import (
    PageNumberPagination,
    LimitOffsetPagination,
    CursorPagination,
    BasePagination
)
from rest_framework.response import Response
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


# ========== 方式1: PageNumberPagination (页码分页) ==========
# 最常用的分页方式，使用页码参数 ?page=2

class AlbumPagination(PageNumberPagination):
    """专辑分页类 - 每页15个专辑"""
    page_size = 15
    page_size_query_param = 'page_size'  # 允许客户端指定每页数量 ?page_size=20
    max_page_size = 100  # 每页最大数量限制


class DjangoPaginatorPagination(BasePagination):
    """基于 Django Paginator 的分页类"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'
    
    def paginate_queryset(self, queryset, request, view=None):
        """
        使用 Django Paginator 进行分页
        """
        self.request = request
        page_size = self.get_page_size(request)
        if page_size is None:
            return None
        
        paginator = Paginator(queryset, page_size)
        page_number = request.query_params.get(self.page_query_param, 1)
        
        try:
            self.page = paginator.page(page_number)
        except PageNotAnInteger:
            self.page = paginator.page(1)
        except EmptyPage:
            self.page = paginator.page(paginator.num_pages)
        
        return list(self.page)
    
    def get_paginated_response(self, data):
        """
        返回分页响应，格式与 DRF 的 PageNumberPagination 兼容
        """
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })
    
    def get_page_size(self, request):
        """
        获取每页数量，支持通过查询参数自定义
        """
        if self.page_size_query_param:
            page_size = request.query_params.get(self.page_size_query_param)
            if page_size:
                try:
                    page_size = int(page_size)
                    if page_size > 0:
                        return min(page_size, self.max_page_size)
                except (KeyError, ValueError):
                    pass
        return self.page_size
    
    def get_next_link(self):
        """
        获取下一页链接
        """
        if not self.page.has_next():
            return None
        url = self.request.build_absolute_uri()
        page_number = self.page.next_page_number()
        return self._replace_query_param(url, self.page_query_param, page_number)
    
    def get_previous_link(self):
        """
        获取上一页链接
        """
        if not self.page.has_previous():
            return None
        url = self.request.build_absolute_uri()
        page_number = self.page.previous_page_number()
        return self._replace_query_param(url, self.page_query_param, page_number)
    
    def _replace_query_param(self, url, key, value):
        """
        替换或添加查询参数
        """
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        query_params[key] = [str(value)]
        
        # page_size 参数已经在 query_params 中（如果存在），无需额外处理
        
        new_query = urlencode(query_params, doseq=True)
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))


class SongPagination(DjangoPaginatorPagination):
    """歌曲分页类 - 每页12首歌曲，使用 Django Paginator"""
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 100


class TimelinePagination(DjangoPaginatorPagination):
    """时间线分页类 - 每页15条，使用 Django Paginator"""
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 100


# ========== 方式2: LimitOffsetPagination (限制偏移分页) ==========
# 使用 ?limit=10&offset=20 的方式，适合需要精确控制偏移量的场景

class LimitOffsetPaginationExample(LimitOffsetPagination):
    """限制偏移分页示例"""
    default_limit = 10  # 默认每页数量
    limit_query_param = 'limit'  # 限制参数名
    offset_query_param = 'offset'  # 偏移参数名
    max_limit = 100  # 最大限制


# ========== 方式3: CursorPagination (游标分页) ==========
# 使用游标（通常是ID或时间戳）进行分页，适合大数据量和实时数据
# 优点：性能好，不会因为新数据插入而重复或遗漏
# 缺点：不支持跳转到指定页码

class CursorPaginationExample(CursorPagination):
    """游标分页示例"""
    page_size = 20
    ordering = '-created_at'  # 必须指定排序字段
    cursor_query_param = 'cursor'  # 游标参数名

