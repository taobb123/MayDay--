"""
视图模块 - API和页面视图
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import render, get_object_or_404
from django.http import FileResponse, Http404
from django.conf import settings
import os
from pathlib import Path
from .models import Album, Song, Tour, Quote, Image
from .serializers import (
    AlbumSerializer, SongSerializer, TourSerializer, 
    QuoteSerializer, ImageSerializer, TimelineItemSerializer
)
from .scanner import MusicScannerProxy, MusicScanner
from .timeline import TimelineRepository
from .messaging import message_queue
from datetime import datetime, timedelta


class AlbumViewSet(viewsets.ModelViewSet):
    """专辑视图集"""
    queryset = Album.objects.all()
    serializer_class = AlbumSerializer


class SongViewSet(viewsets.ModelViewSet):
    """歌曲视图集"""
    queryset = Song.objects.all()
    serializer_class = SongSerializer
    
    @action(detail=False, methods=['get'])
    def by_album(self, request):
        """根据专辑获取歌曲"""
        album_id = request.query_params.get('album_id')
        if album_id:
            songs = Song.objects.filter(album_id=album_id)
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
    """时间线视图"""
    
    def get(self, request):
        """获取时间线数据"""
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
        
        # 序列化数据
        serializer = TimelineItemSerializer(items, many=True)
        
        return Response({
            'timeline': serializer.data,
            'count': len(items)
        })


def index(request):
    """主页视图"""
    timeline_repo = TimelineRepository()
    timeline_data = timeline_repo.get_timeline_data()
    
    context = {
        'timeline_data': timeline_data,
        'albums': Album.objects.all(),  # 显示所有专辑，不再限制数量
        'songs': Song.objects.all()[:20],  # 显示前20首歌曲
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

