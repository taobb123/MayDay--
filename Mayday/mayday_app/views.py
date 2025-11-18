"""
视图模块 - API和页面视图
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
import rest_framework.renderers
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.db.models import Q
from django.http import FileResponse, Http404, JsonResponse
import json
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import os
from pathlib import Path
from .models import Album, Song, Tour, Quote, Image, Playlist, PlaylistSong
from .serializers import (
    AlbumSerializer, SongSerializer, TourSerializer, 
    QuoteSerializer, ImageSerializer, TimelineItemSerializer,
    PlaylistSerializer, PlaylistSongSerializer
)
from .scanner import MusicScannerProxy, MusicScanner
from .timeline import TimelineRepository
from .messaging import message_queue
from .pagination import AlbumPagination, TimelinePagination, SongPagination
from datetime import datetime, timedelta
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, NotAuthenticated


def custom_exception_handler(exc, context):
    """自定义异常处理器，确保API错误返回JSON"""
    # 调用DRF的默认异常处理器
    response = drf_exception_handler(exc, context)
    
    if response is not None:
        # 确保响应是JSON格式
        response['Content-Type'] = 'application/json'
        
        # 如果是认证/权限错误，提供更友好的错误信息
        if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
            response.data = {'error': '请先登录'}
        elif isinstance(exc, PermissionDenied):
            response.data = {'error': '没有权限访问此资源'}
    
    return response


class AlbumViewSet(viewsets.ModelViewSet):
    """专辑视图集"""
    queryset = Album.objects.all().prefetch_related('songs')
    serializer_class = AlbumSerializer
    pagination_class = AlbumPagination


class SongViewSet(viewsets.ModelViewSet):
    """歌曲视图集"""
    queryset = Song.objects.all().select_related('album')
    serializer_class = SongSerializer
    pagination_class = SongPagination  # 为列表视图启用分页
    permission_classes = [AllowAny]  # 允许未登录用户访问歌曲列表
    
    @action(detail=False, methods=['get'])
    def by_album(self, request):
        """根据专辑获取歌曲（支持分页）"""
        album_id = request.query_params.get('album_id')
        if album_id:
            songs = Song.objects.filter(album_id=album_id).select_related('album')
            
            # 应用分页（在自定义action中需要手动处理）
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(songs, request)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(songs, many=True)
            return Response(serializer.data)
        return Response([])
    
    @action(detail=True, methods=['get'])
    def lyrics_file(self, request, pk=None):
        """从文件夹读取歌词文件"""
        from django.conf import settings
        from pathlib import Path
        import re
        
        song = self.get_object()
        lyrics_dir = Path(getattr(settings, 'LYRICS_DIRECTORY', r'C:\Lyrics'))
        
        if not lyrics_dir.exists():
            return Response({
                'error': '歌词目录不存在',
                'lyrics': None
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 支持的歌词文件格式
        lyric_extensions = ['.txt', '.lrc', '.lyric', '.lyrics']
        
        # 规范化歌曲标题用于匹配
        def normalize_text(text):
            # 去除空格、标点符号，转换为小写
            return re.sub(r'[^\w]', '', text.lower())
        
        song_title_normalized = normalize_text(song.title)
        
        # 查找匹配的歌词文件
        lyrics_content = None
        matched_file = None
        
        # 遍历歌词目录中的所有文件
        for lyric_file in lyrics_dir.rglob('*'):
            if lyric_file.is_file() and lyric_file.suffix.lower() in lyric_extensions:
                # 规范化文件名（不含扩展名）
                filename_normalized = normalize_text(lyric_file.stem)
                
                # 尝试匹配
                if (song_title_normalized == filename_normalized or
                    song_title_normalized in filename_normalized or
                    filename_normalized in song_title_normalized):
                    # 读取文件内容
                    try:
                        # 尝试多种编码
                        encodings = ['utf-8', 'gbk', 'gb2312', 'big5', 'latin-1']
                        for encoding in encodings:
                            try:
                                with open(lyric_file, 'r', encoding=encoding) as f:
                                    lyrics_content = f.read().strip()
                                    matched_file = str(lyric_file)
                                    break
                            except UnicodeDecodeError:
                                continue
                        
                        if lyrics_content:
                            break
                    except Exception as e:
                        continue
        
        if lyrics_content:
            return Response({
                'lyrics': lyrics_content,
                'file': matched_file
            })
        else:
            return Response({
                'error': '未找到匹配的歌词文件',
                'lyrics': None
            }, status=status.HTTP_404_NOT_FOUND)


class TourViewSet(viewsets.ModelViewSet):
    """巡回演出视图集"""
    queryset = Tour.objects.all()
    serializer_class = TourSerializer


class QuoteViewSet(viewsets.ModelViewSet):
    """言论视图集"""
    queryset = Quote.objects.all()
    serializer_class = QuoteSerializer


class ImageViewSet(viewsets.ModelViewSet):
    """图片视图集"""
    queryset = Image.objects.all()
    serializer_class = ImageSerializer


class ScanView(APIView):
    """扫描视图"""
    
    def post(self, request):
        """触发扫描任务"""
        directory_path = request.data.get('directory_path', settings.MUSIC_DIRECTORY)
        
        # 使用代理扫描器
        scanner = MusicScannerProxy(MusicScanner())
        
        try:
            # 发送扫描任务到消息队列（异步处理）
            message_queue.send_scan_task(directory_path)
            
            # 也可以同步扫描
            songs = scanner.scan_directory(directory_path)
            
            return Response({
                'status': 'success',
                'message': f'扫描完成，找到 {len(songs)} 首歌曲',
                'songs_count': len(songs)
            })
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TimelineView(APIView):
    """时间线视图 - 支持分页"""
    pagination_class = TimelinePagination
    
    def get(self, request):
        """获取时间线数据（支持分页）"""
        timeline_repo = TimelineRepository()
        
        # 获取日期范围参数
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        
        if start_date_str and end_date_str:
            start_date = datetime.fromisoformat(start_date_str)
            end_date = datetime.fromisoformat(end_date_str)
            items = timeline_repo.get_items_by_date_range(start_date, end_date)
        else:
            items = timeline_repo.get_all_items()
        
        # 应用分页（对列表进行分页）
        paginator = self.pagination_class()
        # 将列表转换为类似queryset的对象以支持分页
        # 注意：PageNumberPagination需要queryset，对于列表我们需要手动处理
        page = paginator.paginate_queryset(items, request)
        
        if page is not None:
            # 序列化分页后的数据
            serializer = TimelineItemSerializer(page, many=True)
            # 返回分页响应
            return paginator.get_paginated_response(serializer.data)
        
        # 如果没有分页参数，返回所有数据（向后兼容）
        serializer = TimelineItemSerializer(items, many=True)
        return Response({
            'timeline': serializer.data,
            'count': len(items)
        })


def index(request):
    """主页视图"""
    # 应用分页：使用 AlbumPagination 的配置
    albums_queryset = Album.objects.all().order_by('-release_date').prefetch_related('songs')  # 按发布日期倒序，预加载歌曲
    albums_paginator = Paginator(albums_queryset, AlbumPagination.page_size)  # 使用 AlbumPagination 的 page_size
    
    album_page = request.GET.get('album_page', 1)
    try:
        albums = albums_paginator.page(album_page)
    except PageNotAnInteger:
        albums = albums_paginator.page(1)
    except EmptyPage:
        albums = albums_paginator.page(albums_paginator.num_pages)
    
    # 应用分页：使用 SongPagination 的配置
    songs_queryset = Song.objects.all().order_by('-id').select_related('album')  # 按ID倒序，显示最新歌曲，预加载专辑
    songs_paginator = Paginator(songs_queryset, SongPagination.page_size)  # 使用 SongPagination 的 page_size
    
    song_page = request.GET.get('song_page', 1)
    try:
        songs = songs_paginator.page(song_page)
    except PageNotAnInteger:
        songs = songs_paginator.page(1)
    except EmptyPage:
        songs = songs_paginator.page(songs_paginator.num_pages)
    
    # 计算歌曲列表的起始索引（用于显示序号）
    songs_start_index = (songs.number - 1) * songs.paginator.per_page + 1
    
    # 获取歌单列表（如果用户已登录）
    playlists = []
    if request.user.is_authenticated:
        playlists = Playlist.objects.filter(user=request.user).prefetch_related('songs').order_by('-created_at')
    
    context = {
        'albums': albums,  # 分页后的专辑对象
        'songs': songs,  # 分页后的歌曲对象
        'songs_start_index': songs_start_index,  # 歌曲列表起始索引
        'playlists': playlists,  # 歌单列表
    }
    
    return render(request, 'mayday_app/index.html', context)


def album_detail(request, album_id):
    """专辑详情页"""
    album = Album.objects.get(id=album_id)
    songs = album.songs.all()
    
    context = {
        'album': album,
        'songs': songs,
    }
    
    return render(request, 'mayday_app/album_detail.html', context)


def play_song(request, song_id):
    """播放歌曲文件视图"""
    from django.http import HttpResponse, JsonResponse
    import mimetypes
    
    song = get_object_or_404(Song, id=song_id)
    
    # 优先使用上传的文件
    if song.file_path and hasattr(song.file_path, 'path'):
        file_path = song.file_path.path
        if os.path.exists(file_path):
            try:
                # 根据文件扩展名设置content_type
                ext = Path(file_path).suffix.lower()
                content_types = {
                    '.mp3': 'audio/mpeg',
                    '.flac': 'audio/flac',
                    '.wav': 'audio/wav',
                    '.m4a': 'audio/mp4',
                    '.aac': 'audio/aac',
                    '.ogg': 'audio/ogg',
                }
                content_type = content_types.get(ext, 'audio/mpeg')
                
                response = FileResponse(open(file_path, 'rb'), content_type=content_type)
                response['Content-Length'] = os.path.getsize(file_path)
                return response
            except Exception as e:
                print(f"读取文件失败: {e}")
                return HttpResponse(f"文件读取失败: {str(e)}", status=500)
    
    # 使用原始文件路径
    if song.original_path:
        # 尝试多种路径格式
        possible_paths = [
            song.original_path,
            Path(song.original_path),
            Path(song.original_path).resolve(),
        ]
        
        last_error = None
        for path_obj in possible_paths:
            try:
                if isinstance(path_obj, str):
                    file_path = Path(path_obj)
                else:
                    file_path = path_obj
                
                # 检查路径是否存在
                if file_path.exists() and file_path.is_file():
                    # 根据文件扩展名设置content_type
                    ext = file_path.suffix.lower()
                    content_types = {
                        '.mp3': 'audio/mpeg',
                        '.flac': 'audio/flac',
                        '.wav': 'audio/wav',
                        '.m4a': 'audio/mp4',
                        '.aac': 'audio/aac',
                        '.ogg': 'audio/ogg',
                    }
                    content_type = content_types.get(ext, 'audio/mpeg')
                    
                    # 使用流式响应，支持大文件
                    file_handle = open(file_path, 'rb')
                    response = FileResponse(file_handle, content_type=content_type)
                    response['Content-Length'] = file_path.stat().st_size
                    # 添加缓存控制头
                    response['Cache-Control'] = 'public, max-age=3600'
                    # 添加Accept-Ranges支持，允许断点续传
                    response['Accept-Ranges'] = 'bytes'
                    return response
                else:
                    # 检查是否是驱动器不存在（外部硬盘断开）
                    drive = file_path.parts[0] if file_path.parts else ''
                    if drive and not os.path.exists(drive):
                        last_error = f"外部存储设备未连接: {drive}"
                    elif not file_path.exists():
                        last_error = f"文件不存在: {file_path}"
            except OSError as e:
                # 操作系统错误，可能是驱动器不存在
                last_error = f"无法访问文件路径: {str(e)}"
                print(f"尝试路径 {path_obj} 失败: {e}")
                continue
            except Exception as e:
                last_error = f"读取文件时出错: {str(e)}"
                print(f"尝试路径 {path_obj} 失败: {e}")
                continue
        
        # 如果所有路径都失败，返回详细的错误信息
        if last_error:
            error_msg = f"歌曲文件无法访问\n\n可能的原因：\n1. 外部硬盘未连接\n2. 文件路径已更改\n3. 文件已被删除\n\n错误详情: {last_error}"
            return HttpResponse(error_msg, status=404, content_type='text/plain; charset=utf-8')
    
    # 如果都失败了，返回404
    return HttpResponse("歌曲文件不存在，请检查外部硬盘是否已连接", status=404, content_type='text/plain; charset=utf-8')


class SearchView(APIView):
    """搜索视图 - 支持歌曲标题和作者模糊搜索"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """搜索歌曲"""
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response({'results': []})
        
        # 模糊搜索歌曲标题和作者
        songs = Song.objects.filter(
            Q(title__icontains=query) | Q(artist__icontains=query)
        ).select_related('album')[:50]  # 限制返回50条
        
        serializer = SongSerializer(songs, many=True)
        return Response({
            'results': serializer.data,
            'count': len(serializer.data)
        })


class ArtistSearchView(APIView):
    """歌手搜索视图 - 支持歌手名称模糊查询和首字母搜索"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """搜索歌手"""
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response({'artists': []})
        
        # 获取所有不重复的歌手名称
        artists = Song.objects.values_list('artist', flat=True).distinct()
        
        # 过滤：支持名称模糊查询
        matching_artists = []
        query_lower = query.lower()
        
        for artist in artists:
            if artist and query_lower in artist.lower():
                matching_artists.append(artist)
        
        # 如果查询是单个字符，也支持首字母搜索
        if len(query) == 1:
            # 获取首字母（支持英文首字母）
            for artist in artists:
                if artist:
                    # 检查英文首字母（不区分大小写）
                    first_char = artist[0].lower()
                    if first_char == query_lower:
                        if artist not in matching_artists:
                            matching_artists.append(artist)
        
        # 去重并排序
        matching_artists = sorted(list(set(matching_artists)))
        
        return Response({
            'artists': matching_artists,
            'count': len(matching_artists)
        })


class ArtistSongsView(APIView):
    """根据歌手获取歌曲列表 - 最多返回12首"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """根据歌手名称获取歌曲"""
        artist = request.query_params.get('artist', '').strip()
        if not artist:
            return Response({'results': [], 'error': '缺少artist参数'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 搜索该歌手的歌曲，最多12首
        songs = Song.objects.filter(
            artist__iexact=artist
        ).select_related('album')[:12]
        
        serializer = SongSerializer(songs, many=True)
        return Response({
            'results': serializer.data,
            'count': len(serializer.data),
            'artist': artist
        })


class ArtistsByInitialView(APIView):
    """获取按拼音首字母分组的歌手列表"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """返回按首字母分组的歌手列表"""
        # 获取所有不重复的歌手，包含拼音信息
        artists_data = Song.objects.values('artist', 'artist_pinyin', 'artist_initial').distinct()
        
        # 按首字母分组
        artists_by_initial = {}
        for item in artists_data:
            artist = item['artist']
            if not artist:
                continue
            
            # 获取首字母，如果没有则尝试生成
            initial = item['artist_initial'] or ''
            if not initial:
                # 如果没有首字母，尝试从拼音获取
                pinyin = item['artist_pinyin'] or ''
                if pinyin:
                    initial = pinyin[0].upper()
                else:
                    # 如果拼音字段也为空，使用pypinyin实时生成
                    try:
                        from pypinyin import lazy_pinyin, Style
                        pinyin_list = lazy_pinyin(artist, style=Style.NORMAL)
                        if pinyin_list and pinyin_list[0]:
                            # 获取第一个字符的拼音首字母
                            initial = pinyin_list[0][0].upper() if pinyin_list[0] else ''
                        else:
                            # 如果是英文，直接取首字母
                            initial = artist[0].upper() if artist else ''
                    except ImportError:
                        # 如果pypinyin未安装，对于英文直接取首字母，中文归类到"#"
                        if artist and artist[0].isalpha():
                            initial = artist[0].upper()
                        else:
                            initial = '#'
            
            # 确保首字母是A-Z
            if initial and initial.isalpha() and initial.isascii():
                initial = initial.upper()
            else:
                # 如果不是字母，归类到"#"
                initial = '#'
            
            if initial not in artists_by_initial:
                artists_by_initial[initial] = []
            
            # 避免重复添加
            if artist not in artists_by_initial[initial]:
                artists_by_initial[initial].append(artist)
        
        # 对每个首字母下的歌手进行排序
        for initial in artists_by_initial:
            artists_by_initial[initial].sort()
        
        # 按首字母排序（A-Z，#放在最后）
        sorted_initials = sorted([k for k in artists_by_initial.keys() if k != '#'])
        if '#' in artists_by_initial:
            sorted_initials.append('#')
        
        # 构建返回数据
        result = {}
        for initial in sorted_initials:
            result[initial] = artists_by_initial[initial]
        
        return Response({
            'artists_by_initial': result,
            'initials': sorted_initials,
            'total_artists': sum(len(artists) for artists in artists_by_initial.values())
        })


class PlaylistViewSet(viewsets.ModelViewSet):
    """歌单视图集"""
    serializer_class = PlaylistSerializer
    permission_classes = [IsAuthenticated]
    queryset = Playlist.objects.all()  # 需要定义queryset，但实际使用get_queryset过滤
    
    def get_queryset(self):
        """只返回当前用户的歌单"""
        return Playlist.objects.filter(user=self.request.user).prefetch_related('songs__song')
    
    def initial(self, request, *args, **kwargs):
        """重写initial方法，确保认证错误返回JSON"""
        try:
            super().initial(request, *args, **kwargs)
        except Exception as exc:
            # 如果是认证或权限错误，返回JSON响应
            if hasattr(exc, 'status_code') and exc.status_code in [401, 403]:
                from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
                if isinstance(exc, AuthenticationFailed):
                    raise AuthenticationFailed({'error': '请先登录'})
                elif isinstance(exc, PermissionDenied):
                    raise PermissionDenied({'error': '没有权限访问此资源'})
            raise
    
    def perform_create(self, serializer):
        """创建歌单时自动设置用户"""
        serializer.save(user=self.request.user)
    
    def get_renderers(self):
        """根据Accept头选择渲染器，优先返回JSON"""
        # 对于所有API路径，强制使用JSON渲染器（不检查Accept头）
        request_path = self.request.path or ''
        if '/api/' in request_path:
            print(f"get_renderers: 检测到API路径 {request_path}，强制使用JSONRenderer")
            return [rest_framework.renderers.JSONRenderer()]
        
        # 检查Accept头
        accept_header = self.request.META.get('HTTP_ACCEPT', '')
        if 'application/json' in accept_header:
            print(f"get_renderers: 检测到Accept: application/json，使用JSONRenderer")
            return [rest_framework.renderers.JSONRenderer()]
        
        print(f"get_renderers: 使用默认渲染器，路径: {request_path}, Accept: {accept_header}")
        return super().get_renderers()
    
    def list(self, request, *args, **kwargs):
        """重写list方法，确保返回JSON响应"""
        try:
            # 调试信息
            request_path = request.path or ''
            accept_header = request.META.get('HTTP_ACCEPT', '')
            print(f"PlaylistViewSet.list - Path: {request_path}, Accept: {accept_header}, User: {request.user}, Authenticated: {request.user.is_authenticated}")
            
            queryset = self.filter_queryset(self.get_queryset())
            
            # 对于所有API路径，强制返回JSON（不依赖Accept头）
            if '/api/' in request_path:
                print("检测到API路径，强制返回JSON")
                page = self.paginate_queryset(queryset)
                if page is not None:
                    serializer = self.get_serializer(page, many=True)
                    response = self.get_paginated_response(serializer.data)
                    # 强制设置Content-Type，确保是JSON
                    response['Content-Type'] = 'application/json; charset=utf-8'
                    print(f"返回分页JSON响应，共 {len(serializer.data)} 条记录")
                    return response
                
                serializer = self.get_serializer(queryset, many=True)
                # 直接返回数据，让JSONRenderer处理（已在get_renderers中强制使用）
                response = Response(serializer.data, content_type='application/json; charset=utf-8')
                print(f"返回JSON响应，共 {len(serializer.data)} 条记录")
                return response
            
            # 检查Accept头
            if 'application/json' in accept_header:
                print("检测到Accept: application/json，返回JSON")
                page = self.paginate_queryset(queryset)
                if page is not None:
                    serializer = self.get_serializer(page, many=True)
                    response = self.get_paginated_response(serializer.data)
                    response['Content-Type'] = 'application/json; charset=utf-8'
                    return response
                
                serializer = self.get_serializer(queryset, many=True)
                response = Response(serializer.data, content_type='application/json; charset=utf-8')
                return response
            
            # 默认行为：对于API路径，即使没有Accept头也返回JSON
            print("使用默认行为，但强制返回JSON")
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                response = self.get_paginated_response(serializer.data)
                response['Content-Type'] = 'application/json; charset=utf-8'
                return response
            
            serializer = self.get_serializer(queryset, many=True)
            response = Response(serializer.data, content_type='application/json; charset=utf-8')
            return response
        except Exception as e:
            # 捕获所有异常，确保返回JSON错误响应
            import traceback
            error_detail = traceback.format_exc()
            print(f"PlaylistViewSet.list 异常: {error_detail}")
            error_data = {'error': f'服务器错误: {str(e)}'}
            return Response(
                error_data,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content_type='application/json; charset=utf-8'
            )
    
    def create(self, request, *args, **kwargs):
        """重写create方法，确保返回JSON响应"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        """重写update方法，确保返回JSON响应"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_song(self, request, pk=None):
        """添加歌曲到歌单"""
        playlist = self.get_object()
        song_id = request.data.get('song_id')
        
        # 调试信息
        print(f"add_song API调用 - Playlist ID: {pk}, Song ID: {song_id}, User: {request.user}")
        print(f"Request data: {request.data}")
        
        if not song_id:
            print("错误: 缺少song_id参数")
            return Response({'error': '缺少song_id参数'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 确保song_id是整数
        try:
            song_id = int(song_id)
        except (ValueError, TypeError):
            print(f"错误: song_id不是有效的整数: {song_id}")
            return Response({'error': 'song_id必须是整数'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            song = Song.objects.get(id=song_id)
        except Song.DoesNotExist:
            print(f"错误: 歌曲不存在 - Song ID: {song_id}")
            return Response({'error': '歌曲不存在'}, status=status.HTTP_404_NOT_FOUND)
        
        # 检查是否已存在
        if PlaylistSong.objects.filter(playlist=playlist, song=song).exists():
            print(f"警告: 歌曲已在歌单中 - Playlist: {playlist.name}, Song: {song.title}")
            return Response({'error': '歌曲已在歌单中'}, status=status.HTTP_400_BAD_REQUEST)
        
        playlist_song = PlaylistSong.objects.create(playlist=playlist, song=song)
        serializer = PlaylistSongSerializer(playlist_song)
        print(f"成功: 歌曲已添加到歌单 - Playlist: {playlist.name}, Song: {song.title}")
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['delete'])
    def remove_song(self, request, pk=None):
        """从歌单移除歌曲"""
        playlist = self.get_object()
        song_id = request.data.get('song_id')
        
        if not song_id:
            return Response({'error': '缺少song_id参数'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            playlist_song = PlaylistSong.objects.get(playlist=playlist, song_id=song_id)
            playlist_song.delete()
            return Response({'message': '已从歌单移除'}, status=status.HTTP_200_OK)
        except PlaylistSong.DoesNotExist:
            return Response({'error': '歌曲不在歌单中'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def move_song(self, request, pk=None):
        """将歌曲移动到另一个歌单"""
        playlist = self.get_object()
        song_id = request.data.get('song_id')
        target_playlist_id = request.data.get('target_playlist_id')
        
        if not song_id or not target_playlist_id:
            return Response({'error': '缺少必要参数'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            target_playlist = Playlist.objects.get(id=target_playlist_id, user=request.user)
        except Playlist.DoesNotExist:
            return Response({'error': '目标歌单不存在'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            playlist_song = PlaylistSong.objects.get(playlist=playlist, song_id=song_id)
            song = playlist_song.song
            
            # 从原歌单删除
            playlist_song.delete()
            
            # 添加到新歌单（如果不存在）
            if not PlaylistSong.objects.filter(playlist=target_playlist, song=song).exists():
                PlaylistSong.objects.create(playlist=target_playlist, song=song)
            
            return Response({'message': '歌曲已移动'}, status=status.HTTP_200_OK)
        except PlaylistSong.DoesNotExist:
            return Response({'error': '歌曲不在歌单中'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    def save_temp_list(self, request):
        """将临时列表保存为歌单"""
        playlist_name = request.data.get('name')
        song_ids = request.data.get('song_ids', [])
        
        if not playlist_name:
            return Response({'error': '缺少歌单名称'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 检查是否已存在同名歌单
        if Playlist.objects.filter(user=request.user, name=playlist_name).exists():
            return Response({'error': '歌单名称已存在'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 创建歌单
        playlist = Playlist.objects.create(user=request.user, name=playlist_name)
        
        # 添加歌曲
        songs = Song.objects.filter(id__in=song_ids)
        for song in songs:
            PlaylistSong.objects.create(playlist=playlist, song=song)
        
        serializer = self.get_serializer(playlist)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# 用户认证视图
@csrf_protect
def login_view(request):
    """登录视图"""
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'index')
            return redirect(next_url)
        else:
            return render(request, 'mayday_app/login.html', {
                'error': '用户名或密码错误'
            })
    
    return render(request, 'mayday_app/login.html')


@csrf_protect
def register_view(request):
    """注册视图"""
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
    else:
        form = UserCreationForm()
    
    return render(request, 'mayday_app/register.html', {'form': form})


def logout_view(request):
    """登出视图"""
    logout(request)
    return redirect('index')


@login_required
def playlist_list_view(request):
    """歌单列表页面"""
    playlists = Playlist.objects.filter(user=request.user).prefetch_related('songs')
    return render(request, 'mayday_app/playlist_list.html', {
        'playlists': playlists
    })


@login_required
def create_playlist_api(request):
    """创建歌单API - 使用JsonResponse确保返回JSON"""
    # 调试信息
    print(f"create_playlist_api called - Method: {request.method}, User: {request.user}, Authenticated: {request.user.is_authenticated}")
    
    if request.method != 'POST':
        print(f"Method not allowed: {request.method}")
        return JsonResponse({'error': f'只支持POST请求，收到: {request.method}'}, status=405)
    
    try:
        # 解析JSON请求体
        if request.content_type and 'application/json' in request.content_type:
            try:
                data = json.loads(request.body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                return JsonResponse({'error': f'无效的JSON数据: {str(e)}'}, status=400)
        else:
            # 兼容form-data格式
            data = request.POST
        
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        # 验证歌单名称
        if not name:
            return JsonResponse({'error': '歌单名称不能为空'}, status=400)
        
        if len(name) > 200:
            return JsonResponse({'error': '歌单名称不能超过200个字符'}, status=400)
        
        # 检查是否已存在同名歌单
        if Playlist.objects.filter(user=request.user, name=name).exists():
            return JsonResponse({'error': '歌单名称已存在'}, status=400)
        
        # 创建歌单
        playlist = Playlist.objects.create(
            user=request.user,
            name=name,
        )
        
        return JsonResponse({
            'message': '歌单创建成功',
            'playlist': {
                'id': playlist.id,
                'name': playlist.name,
                'song_count': 0,
                'created_at': playlist.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        }, status=201)
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"创建歌单错误: {error_detail}")
        return JsonResponse({'error': f'创建失败: {str(e)}'}, status=500)


@login_required
def update_playlist_api(request, playlist_id):
    """更新歌单API - 使用JsonResponse确保返回JSON"""
    if request.method not in ['PUT', 'PATCH']:
        return JsonResponse({'error': '只支持PUT/PATCH请求'}, status=405)
    
    try:
        playlist = Playlist.objects.get(id=playlist_id, user=request.user)
    except Playlist.DoesNotExist:
        return JsonResponse({'error': '歌单不存在'}, status=404)
    
    try:
        # 解析JSON请求体
        if request.content_type and 'application/json' in request.content_type:
            try:
                data = json.loads(request.body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                return JsonResponse({'error': f'无效的JSON数据: {str(e)}'}, status=400)
        else:
            data = request.POST
        
        name = data.get('name', '').strip()
        
        # 验证歌单名称
        if not name:
            return JsonResponse({'error': '歌单名称不能为空'}, status=400)
        
        if len(name) > 200:
            return JsonResponse({'error': '歌单名称不能超过200个字符'}, status=400)
        
        # 检查是否与其他歌单重名
        if Playlist.objects.filter(user=request.user, name=name).exclude(id=playlist_id).exists():
            return JsonResponse({'error': '歌单名称已存在'}, status=400)
        
        # 更新歌单
        playlist.name = name
        playlist.save()
        
        return JsonResponse({
            'message': '歌单更新成功',
            'playlist': {
                'id': playlist.id,
                'name': playlist.name,
                'song_count': playlist.get_song_count(),
                'updated_at': playlist.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"更新歌单错误: {error_detail}")
        return JsonResponse({'error': f'更新失败: {str(e)}'}, status=500)


def delete_playlist_api(request, playlist_id):
    """删除歌单API - 使用JsonResponse确保返回JSON"""
    if request.method != 'DELETE':
        return JsonResponse({'error': '只支持DELETE请求'}, status=405)
    
    try:
        playlist = Playlist.objects.get(id=playlist_id)
        playlist_name = playlist.name
        playlist.delete()
        return JsonResponse({'message': f'歌单"{playlist_name}"已删除'})
    except Playlist.DoesNotExist:
        return JsonResponse({'error': '歌单不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'删除失败: {str(e)}'}, status=500)


@login_required
def get_playlists_api(request):
    """获取用户歌单列表API - 使用JsonResponse确保返回JSON"""
    """GET /api/playlists/list/ - 返回当前用户的歌单列表，供"添加到歌单"弹窗选择"""
    if request.method != 'GET':
        return JsonResponse({'error': '只支持GET请求'}, status=405)
    
    try:
        # 获取当前用户的所有歌单
        playlists = Playlist.objects.filter(user=request.user).order_by('-created_at')
        
        # 构建简单的歌单列表（只包含id和name，供选择使用）
        playlist_list = [
            {
                'id': playlist.id,
                'name': playlist.name,
                'song_count': playlist.get_song_count()
            }
            for playlist in playlists
        ]
        
        return JsonResponse(playlist_list, safe=False)
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"获取歌单列表错误: {error_detail}")
        return JsonResponse({'error': f'获取失败: {str(e)}'}, status=500)


@login_required
def add_song_to_playlist_api(request, playlist_id):
    """添加歌曲到歌单API - 使用JsonResponse确保返回JSON"""
    """POST /api/playlists/{playlist_id}/add_song/ - 添加歌曲到指定歌单"""
    if request.method != 'POST':
        return JsonResponse({'error': '只支持POST请求'}, status=405)
    
    try:
        # 验证歌单是否存在且属于当前用户
        try:
            playlist = Playlist.objects.get(id=playlist_id, user=request.user)
        except Playlist.DoesNotExist:
            return JsonResponse({'error': '歌单不存在'}, status=404)
        
        # 解析请求体
        if request.content_type and 'application/json' in request.content_type:
            try:
                data = json.loads(request.body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                return JsonResponse({'error': f'无效的JSON数据: {str(e)}'}, status=400)
        else:
            data = request.POST
        
        song_id = data.get('song_id')
        if not song_id:
            return JsonResponse({'error': '缺少song_id参数'}, status=400)
        
        # 确保song_id是整数
        try:
            song_id = int(song_id)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'song_id必须是整数'}, status=400)
        
        # 验证歌曲是否存在
        try:
            song = Song.objects.get(id=song_id)
        except Song.DoesNotExist:
            return JsonResponse({'error': '歌曲不存在'}, status=404)
        
        # 检查是否已存在（使用get_or_create防止重复）
        playlist_song, created = PlaylistSong.objects.get_or_create(
            playlist=playlist,
            song=song
        )
        
        if not created:
            return JsonResponse({
                'success': False,
                'message': '歌曲已在歌单中',
                'playlist_name': playlist.name
            }, status=200)
        
        return JsonResponse({
            'success': True,
            'message': f'歌曲已添加到歌单「{playlist.name}」',
            'playlist_name': playlist.name
        }, status=201)
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"添加歌曲到歌单错误: {error_detail}")
        return JsonResponse({'error': f'添加失败: {str(e)}'}, status=500)


def remove_song_from_playlist_api(request, playlist_id, song_id):
    """从歌单移除歌曲API - 使用JsonResponse确保返回JSON"""
    """DELETE /api/playlists/{playlist_id}/songs/{song_id}/ - 从指定歌单移除歌曲"""
    if request.method != 'DELETE':
        return JsonResponse({'error': '只支持DELETE请求'}, status=405)
    
    try:
        # 验证歌单是否存在
        try:
            playlist = Playlist.objects.get(id=playlist_id)
        except Playlist.DoesNotExist:
            return JsonResponse({'error': '歌单不存在'}, status=404)
        
        # 验证歌曲是否存在
        try:
            song = Song.objects.get(id=song_id)
        except Song.DoesNotExist:
            return JsonResponse({'error': '歌曲不存在'}, status=404)
        
        # 删除关联
        try:
            playlist_song = PlaylistSong.objects.get(playlist=playlist, song=song)
            playlist_song.delete()
            return JsonResponse({'message': '歌曲已从歌单移除'}, status=200)
        except PlaylistSong.DoesNotExist:
            return JsonResponse({'error': '歌曲不在歌单中'}, status=404)
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"从歌单移除歌曲错误: {error_detail}")
        return JsonResponse({'error': f'移除失败: {str(e)}'}, status=500)


@login_required
def playlist_detail_view(request, playlist_id):
    """歌单详情页面"""
    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
    playlist_songs = playlist.songs.select_related('song', 'song__album').all()
    return render(request, 'mayday_app/playlist_detail.html', {
        'playlist': playlist,
        'playlist_songs': playlist_songs
    })

