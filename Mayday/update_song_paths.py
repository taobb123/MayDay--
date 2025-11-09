"""
更新现有歌曲的原始文件路径
"""
import os
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mayday_project.settings')
django.setup()

from django.conf import settings
from mayday_app.models import Song

def update_song_paths():
    """更新歌曲的原始文件路径"""
    music_dir = Path(settings.MUSIC_DIRECTORY)
    
    if not music_dir.exists():
        print(f"音乐目录不存在: {music_dir}")
        return
    
    # 支持的音频格式
    supported_formats = {'.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg'}
    
    # 扫描所有音频文件
    audio_files = {}
    for file_path in music_dir.rglob('*'):
        if file_path.suffix.lower() in supported_formats:
            # 使用文件名作为键
            key = file_path.stem.lower()
            audio_files[key] = str(file_path)
    
    print(f"找到 {len(audio_files)} 个音频文件")
    
    # 更新歌曲路径
    updated_count = 0
    for song in Song.objects.all():
        # 尝试匹配文件名
        song_key = song.title.lower()
        matched_path = None
        
        # 精确匹配
        if song_key in audio_files:
            matched_path = audio_files[song_key]
        else:
            # 模糊匹配：查找包含歌曲标题的文件
            for file_key, file_path in audio_files.items():
                if song_key in file_key or file_key in song_key:
                    matched_path = file_path
                    break
        
        if matched_path and Path(matched_path).exists():
            if song.original_path != matched_path:
                song.original_path = matched_path
                song.save()
                print(f"✓ 更新: {song.title} -> {matched_path}")
                updated_count += 1
        else:
            print(f"✗ 未找到: {song.title}")
    
    print(f"\n更新完成！共更新 {updated_count} 首歌曲")

if __name__ == '__main__':
    update_song_paths()

