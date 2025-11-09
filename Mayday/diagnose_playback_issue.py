"""
诊断播放问题：检查是数据库、组件还是文件系统问题
"""
import os
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mayday_project.settings')
django.setup()

from mayday_app.models import Song
from django.conf import settings

def diagnose():
    """诊断播放问题"""
    print("=" * 80)
    print("播放问题诊断报告")
    print("=" * 80)
    
    # 1. 检查数据库
    print("\n1. 数据库层面检查:")
    total_songs = Song.objects.count()
    songs_with_path = Song.objects.exclude(original_path='').count()
    print(f"   总歌曲数: {total_songs}")
    print(f"   有路径记录的歌曲: {songs_with_path}")
    
    # 2. 检查文件系统
    print("\n2. 文件系统层面检查:")
    music_dir = Path(settings.MUSIC_DIRECTORY)
    print(f"   配置的音乐目录: {music_dir}")
    print(f"   目录是否存在: {music_dir.exists()}")
    
    if music_dir.exists():
        # 检查目录中的文件
        audio_files = list(music_dir.rglob('*.flac')) + list(music_dir.rglob('*.mp3'))
        print(f"   找到音频文件数: {len(audio_files)}")
        if audio_files:
            print(f"   示例文件: {audio_files[0]}")
    else:
        print("   ⚠️ 音乐目录不存在！")
        # 尝试查找可能的目录
        print("\n   尝试查找可能的音乐目录:")
        for drive in ['D:', 'C:', 'E:', 'F:']:
            if os.path.exists(drive):
                possible_path = Path(f"{drive}\\Music\\五月天")
                if possible_path.exists():
                    print(f"   ✓ 找到: {possible_path}")
    
    # 3. 检查数据库中的路径是否对应实际文件
    print("\n3. 数据一致性检查:")
    sample_songs = Song.objects.exclude(original_path='')[:5]
    found_count = 0
    missing_count = 0
    
    for song in sample_songs:
        if song.original_path:
            file_path = Path(song.original_path)
            exists = file_path.exists() and file_path.is_file()
            if exists:
                found_count += 1
                print(f"   ✓ {song.title}: 文件存在")
            else:
                missing_count += 1
                print(f"   ✗ {song.title}: 文件不存在 ({song.original_path})")
    
    # 4. 问题定位
    print("\n" + "=" * 80)
    print("问题定位:")
    print("=" * 80)
    
    if not music_dir.exists():
        print("❌ 问题类型: 文件系统层面")
        print("   原因: 配置的音乐目录不存在")
        print("   解决: 检查 settings.py 中的 MUSIC_DIRECTORY 配置，或文件已被移动/删除")
    elif missing_count > found_count:
        print("❌ 问题类型: 数据一致性问题")
        print("   原因: 数据库中的文件路径与实际文件系统不一致")
        print("   解决: 重新扫描音乐目录以更新数据库路径")
    else:
        print("✓ 文件系统正常，可能是组件层面的问题")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    diagnose()

