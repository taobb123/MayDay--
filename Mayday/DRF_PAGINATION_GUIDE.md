# DRF 分页功能完整指南

本文档详细说明 Django REST Framework (DRF) 中如何实现视图的分页功能，以及如何与现有视图集成。

## 📚 目录

1. [DRF 分页的三种方式](#drf-分页的三种方式)
2. [与现有视图集成](#与现有视图集成)
3. [实际应用示例](#实际应用示例)
4. [最佳实践](#最佳实践)

---

## DRF 分页的三种方式

### 1. PageNumberPagination（页码分页）⭐ 最常用

**特点：**
- 使用页码参数 `?page=2`
- 适合大多数场景
- 支持跳转到指定页码

**响应格式：**
```json
{
  "count": 100,
  "next": "http://example.com/api/albums/?page=3",
  "previous": "http://example.com/api/albums/?page=1",
  "results": [...]
}
```

**配置示例：**
```python
from rest_framework.pagination import PageNumberPagination

class AlbumPagination(PageNumberPagination):
    page_size = 10                    # 每页默认数量
    page_size_query_param = 'page_size'  # 允许客户端指定每页数量
    max_page_size = 100               # 每页最大数量限制
```

**使用方式：**
```python
class AlbumViewSet(viewsets.ModelViewSet):
    queryset = Album.objects.all()
    serializer_class = AlbumSerializer
    pagination_class = AlbumPagination  # 指定分页类
```

**API 调用：**
- `GET /api/albums/` - 第1页（10个）
- `GET /api/albums/?page=2` - 第2页
- `GET /api/albums/?page_size=20` - 临时设置每页20个

---

### 2. LimitOffsetPagination（限制偏移分页）

**特点：**
- 使用 `?limit=10&offset=20`
- 适合需要精确控制偏移量的场景
- 类似 SQL 的 LIMIT/OFFSET

**响应格式：**
```json
{
  "count": 100,
  "next": "http://example.com/api/albums/?limit=10&offset=20",
  "previous": "http://example.com/api/albums/?limit=10&offset=0",
  "results": [...]
}
```

**配置示例：**
```python
from rest_framework.pagination import LimitOffsetPagination

class LimitOffsetPaginationExample(LimitOffsetPagination):
    default_limit = 10
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    max_limit = 100
```

**API 调用：**
- `GET /api/albums/?limit=10&offset=0` - 前10条
- `GET /api/albums/?limit=10&offset=10` - 第11-20条

---

### 3. CursorPagination（游标分页）

**特点：**
- 使用游标（通常是ID或时间戳）进行分页
- 适合大数据量和实时数据
- **优点：** 性能好，不会因为新数据插入而重复或遗漏
- **缺点：** 不支持跳转到指定页码

**响应格式：**
```json
{
  "next": "http://example.com/api/albums/?cursor=cD0yMDIzLTEyLTAx",
  "previous": null,
  "results": [...]
}
```

**配置示例：**
```python
from rest_framework.pagination import CursorPagination

class CursorPaginationExample(CursorPagination):
    page_size = 20
    ordering = '-created_at'  # 必须指定排序字段
    cursor_query_param = 'cursor'
```

---

## 与现有视图集成

### ✅ 方式1: ViewSet（自动支持）

**ModelViewSet / ReadOnlyModelViewSet** 自动支持分页，只需设置 `pagination_class`：

```python
class AlbumViewSet(viewsets.ModelViewSet):
    queryset = Album.objects.all()
    serializer_class = AlbumSerializer
    pagination_class = AlbumPagination  # 只需这一行！
```

**优点：**
- 最简单，自动处理
- 所有列表操作（list, retrieve）都支持分页

---

### ✅ 方式2: GenericAPIView（ListAPIView, RetrieveAPIView）

**ListAPIView** 也自动支持分页：

```python
from rest_framework.generics import ListAPIView

class AlbumListView(ListAPIView):
    queryset = Album.objects.all()
    serializer_class = AlbumSerializer
    pagination_class = AlbumPagination  # 自动支持分页
```

---

### ⚠️ 方式3: APIView（需要手动处理）

**APIView** 不会自动应用分页，需要手动处理：

```python
from rest_framework.views import APIView
from rest_framework.response import Response

class TimelineView(APIView):
    pagination_class = TimelinePagination
    
    def get(self, request):
        # 获取数据
        items = timeline_repo.get_all_items()
        
        # 手动应用分页
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(items, request)
        
        if page is not None:
            # 序列化分页后的数据
            serializer = TimelineItemSerializer(page, many=True)
            # 返回分页响应
            return paginator.get_paginated_response(serializer.data)
        
        # 如果没有分页参数，返回所有数据
        serializer = TimelineItemSerializer(items, many=True)
        return Response(serializer.data)
```

**关键点：**
1. 设置 `pagination_class` 属性
2. 调用 `paginator.paginate_queryset(queryset, request)`
3. 如果返回 `None`，说明不需要分页
4. 使用 `paginator.get_paginated_response(data)` 返回分页响应

---

### ✅ 方式4: ViewSet 中的自定义 Action

在 ViewSet 的自定义 `@action` 中也可以使用分页：

```python
class SongViewSet(viewsets.ModelViewSet):
    queryset = Song.objects.all()
    serializer_class = SongSerializer
    
    @action(detail=False, methods=['get'])
    def by_album(self, request):
        """根据专辑获取歌曲（支持分页）"""
        album_id = request.query_params.get('album_id')
        if album_id:
            songs = Song.objects.filter(album_id=album_id)
            
            # 应用分页
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(songs, request)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(songs, many=True)
            return Response(serializer.data)
        return Response([])
```

---

## 实际应用示例

### 示例1: 专辑列表分页（已实现）

```python
# pagination.py
class AlbumPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

# views.py
class AlbumViewSet(viewsets.ModelViewSet):
    queryset = Album.objects.all()
    serializer_class = AlbumSerializer
    pagination_class = AlbumPagination
```

**测试：**
```bash
# 获取第1页
curl http://localhost:8000/api/albums/

# 获取第2页
curl http://localhost:8000/api/albums/?page=2

# 每页20个
curl http://localhost:8000/api/albums/?page_size=20
```

---

### 示例2: 时间线视图分页（已实现）

```python
# pagination.py
class TimelinePagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 50

# views.py
class TimelineView(APIView):
    pagination_class = TimelinePagination
    
    def get(self, request):
        items = timeline_repo.get_all_items()
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(items, request)
        
        if page is not None:
            serializer = TimelineItemSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = TimelineItemSerializer(items, many=True)
        return Response({'timeline': serializer.data, 'count': len(items)})
```

---

## 最佳实践

### 1. 全局配置 vs 视图级配置

**全局配置（settings.py）：**
```python
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,  # 默认每页20条
}
```

**视图级配置（推荐）：**
- 不同资源可能需要不同的分页大小
- 更灵活，可以覆盖全局设置

```python
class AlbumViewSet(viewsets.ModelViewSet):
    pagination_class = AlbumPagination  # 覆盖全局设置
```

---

### 2. 分页类命名规范

建议使用 `{ModelName}Pagination` 命名：
- `AlbumPagination`
- `SongPagination`
- `TimelinePagination`

---

### 3. 分页大小建议

- **小列表（< 50条）：** `page_size = 10-20`
- **中等列表（50-500条）：** `page_size = 20-50`
- **大列表（> 500条）：** `page_size = 50-100`

---

### 4. 允许客户端调整每页数量

```python
class AlbumPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'  # 允许 ?page_size=20
    max_page_size = 100  # 防止客户端请求过大
```

---

### 5. 禁用特定视图的分页

```python
class AlbumViewSet(viewsets.ModelViewSet):
    queryset = Album.objects.all()
    serializer_class = AlbumSerializer
    pagination_class = None  # 禁用分页
```

---

## 总结

| 视图类型 | 分页支持 | 配置方式 |
|---------|---------|---------|
| ModelViewSet | ✅ 自动 | `pagination_class = XxxPagination` |
| ReadOnlyModelViewSet | ✅ 自动 | `pagination_class = XxxPagination` |
| ListAPIView | ✅ 自动 | `pagination_class = XxxPagination` |
| APIView | ⚠️ 手动 | 需要调用 `paginate_queryset()` |
| 自定义 @action | ⚠️ 手动 | 需要调用 `paginate_queryset()` |

**推荐：**
- 优先使用 `ViewSet` 或 `ListAPIView`，自动支持分页
- 对于 `APIView`，手动实现分页逻辑
- 为不同资源创建专门的分页类，便于维护

---

## 相关文件

- `mayday_app/pagination.py` - 分页类定义
- `mayday_app/views.py` - 视图实现
- `mayday_project/settings.py` - 全局DRF配置

