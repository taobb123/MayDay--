"""
检查歌曲文件是否存在，并诊断问题
"""
import os
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mayday_project.settings')
django.setup()

from mayday_app.models import Song

def check_song_files():
    """检查歌曲文件是否存在"""
    songs = Song.objects.all()
    
    print(f"总共 {songs.count()} 首歌曲\n")
    print("=" * 80)
    
    missing_count = 0
    found_count = 0
    
    for song in songs:
        found = False
        file_path = None
        
        # 检查 file_path（上传的文件）
        if song.file_path and hasattr(song.file_path, 'path'):
            file_path = song.file_path.path
            if os.path.exists(file_path):
                found = True
                print(f"✓ ID:{song.id} {song.title}")
                print(f"  文件路径: {file_path}")
        
        # 检查 original_path（原始文件路径）
        if not found and song.original_path:
            # 尝试多种路径格式
            possible_paths = [
                song.original_path,
                Path(song.original_path),
                Path(song.original_path).resolve(),
            ]
            
            for path_obj in possible_paths:
                try:
                    if isinstance(path_obj, str):
                        file_path = Path(path_obj)
                    else:
                        file_path = path_obj
                    
                    if file_path.exists() and file_path.is_file():
                        found = True
                        print(f"✓ ID:{song.id} {song.title}")
                        print(f"  文件路径: {file_path}")
                        break
                except Exception as e:
                    continue
        
        if not found:
            missing_count += 1
            print(f"✗ ID:{song.id} {song.title}")
            if song.original_path:
                print(f"  数据库路径: {song.original_path}")
            if song.file_path:
                print(f"  上传文件: {song.file_path}")
            print(f"  状态: 文件不存在")
        else:
            found_count += 1
        
        print("-" * 80)
    
    print("\n" + "=" * 80)
    print(f"统计结果:")
    print(f"  找到文件: {found_count} 首")
    print(f"  缺失文件: {missing_count} 首")
    print(f"  总计: {songs.count()} 首")

if __name__ == '__main__':
    check_song_files()

