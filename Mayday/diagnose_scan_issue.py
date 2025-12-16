"""
诊断扫描功能失败的原因
"""
import os
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mayday_project.settings')
django.setup()

from django.conf import settings
from mayday_app.scanner import MusicScannerProxy, MusicScanner

def diagnose_scan():
    """诊断扫描问题"""
    print("=" * 60)
    print("扫描功能诊断")
    print("=" * 60)
    print()
    
    # 1. 检查配置的目录
    music_dir = settings.MUSIC_DIRECTORY
    print(f"1. 配置的音乐目录: {music_dir}")
    
    music_path = Path(music_dir)
    print(f"   目录是否存在: {music_path.exists()}")
    
    if music_path.exists():
        print(f"   是否为目录: {music_path.is_dir()}")
        print(f"   是否可读: {os.access(music_dir, os.R_OK)}")
        
        # 检查是否有音频文件
        scanner = MusicScanner()
        audio_files = []
        try:
            for file_path in music_path.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in scanner.SUPPORTED_FORMATS:
                    audio_files.append(file_path)
        except Exception as e:
            print(f"   [ERROR] 扫描文件时出错: {e}")
        
        print(f"   找到的音频文件数: {len(audio_files)}")
        if len(audio_files) > 0:
            print(f"   示例文件: {audio_files[0]}")
    else:
        print(f"   [ERROR] 目录不存在！")
        # 检查父目录
        parent = music_path.parent
        print(f"   父目录是否存在: {parent.exists()}")
        if parent.exists():
            print(f"   父目录内容: {list(parent.iterdir())[:5]}")
    
    print()
    
    # 2. 测试扫描功能
    print("2. 测试扫描功能")
    try:
        scanner = MusicScannerProxy(MusicScanner())
        print(f"   开始扫描目录: {music_dir}")
        songs = scanner.scan_directory(music_dir)
        print(f"   [OK] 扫描完成，找到 {len(songs)} 首歌曲")
        
        if len(songs) == 0:
            print("   [WARNING] 没有找到歌曲，可能的原因：")
            print("      - 目录中没有支持的音频文件")
            print("      - 文件格式不在支持列表中")
            print("      - 文件权限问题")
    except Exception as e:
        print(f"   [ERROR] 扫描失败: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # 3. 检查支持的格式
    print("3. 支持的音频格式:")
    scanner = MusicScanner()
    for fmt in scanner.SUPPORTED_FORMATS:
        print(f"   - {fmt}")
    
    print()
    
    # 4. 检查数据库连接
    print("4. 检查数据库连接")
    try:
        from mayday_app.models import Song, Album
        song_count = Song.objects.count()
        album_count = Album.objects.count()
        print(f"   [OK] 数据库连接正常")
        print(f"   当前歌曲数: {song_count}")
        print(f"   当前专辑数: {album_count}")
    except Exception as e:
        print(f"   [ERROR] 数据库连接失败: {e}")
    
    print()
    print("=" * 60)

if __name__ == '__main__':
    diagnose_scan()

