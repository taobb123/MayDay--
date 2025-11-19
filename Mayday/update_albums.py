"""
更新专辑列表 - 重新扫描音乐目录
"""
import os
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mayday_project.settings')
django.setup()

from django.conf import settings
from mayday_app.scanner import MusicScannerProxy, MusicScanner

def update_albums():
    """更新专辑列表 - 扫描音乐目录"""
    # 使用默认的音乐目录，或者从设置中获取
    music_dir = settings.MUSIC_DIRECTORY
    
    print("=" * 50)
    print("更新专辑列表")
    print("=" * 50)
    print(f"扫描目录: {music_dir}")
    print(f"允许创建专辑的目录: D:\\Music\\五月天")
    print()
    
    # 检查目录是否存在
    if not Path(music_dir).exists():
        print(f"❌ 错误: 音乐目录不存在: {music_dir}")
        return
    
    # 使用代理扫描器
    scanner = MusicScannerProxy(MusicScanner())
    
    try:
        print("开始扫描...")
        songs = scanner.scan_directory(music_dir)
        
        print(f"\n✓ 扫描完成！")
        print(f"  找到 {len(songs)} 首歌曲")
        
        # 统计专辑数量
        from mayday_app.models import Album
        album_count = Album.objects.count()
        print(f"  当前共有 {album_count} 个专辑")
        
        print("\n注意: 只有从 D:\\Music\\五月天 目录扫描的文件才会创建新专辑")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ 扫描失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    update_albums()

