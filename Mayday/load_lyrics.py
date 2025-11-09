"""
从 C:\Lyrics 目录加载歌词到数据库
支持多种歌词文件格式：.txt, .lrc 等
"""
import os
import django
from pathlib import Path
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mayday_project.settings')
django.setup()

from mayday_app.models import Song


def normalize_text(text):
    """规范化文本，用于匹配"""
    # 去除空格、标点符号，转换为小写
    text = re.sub(r'[^\w]', '', text.lower())
    return text


def match_lyric_file_to_song(lyric_filename, songs):
    """
    匹配歌词文件到歌曲
    
    Args:
        lyric_filename: 歌词文件名（不含扩展名）
        songs: 歌曲查询集
    
    Returns:
        匹配的歌曲对象，如果没有匹配则返回None
    """
    # 规范化歌词文件名
    normalized_lyric = normalize_text(lyric_filename)
    
    best_match = None
    best_score = 0
    
    for song in songs:
        # 规范化歌曲标题
        normalized_title = normalize_text(song.title)
        
        # 计算匹配分数
        score = 0
        
        # 精确匹配
        if normalized_lyric == normalized_title:
            score = 100
        # 歌词文件名包含歌曲标题
        elif normalized_title in normalized_lyric:
            score = 80 + len(normalized_title) / len(normalized_lyric) * 20
        # 歌曲标题包含歌词文件名
        elif normalized_lyric in normalized_title:
            score = 60 + len(normalized_lyric) / len(normalized_title) * 20
        # 部分匹配（至少50%字符相同）
        else:
            common_chars = set(normalized_lyric) & set(normalized_title)
            if common_chars:
                similarity = len(common_chars) / max(len(set(normalized_lyric)), len(set(normalized_title)))
                if similarity > 0.5:
                    score = similarity * 50
        
        if score > best_score:
            best_score = score
            best_match = song
    
    # 只返回匹配度较高的结果（阈值60）
    if best_score >= 60:
        return best_match
    return None


def read_lyric_file(file_path):
    """
    读取歌词文件内容
    
    Args:
        file_path: 歌词文件路径
    
    Returns:
        歌词内容字符串
    """
    try:
        # 尝试多种编码
        encodings = ['utf-8', 'gbk', 'gb2312', 'big5', 'latin-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    # 清理内容
                    content = content.strip()
                    return content
            except UnicodeDecodeError:
                continue
        
        # 如果所有编码都失败，使用二进制模式读取
        with open(file_path, 'rb') as f:
            content = f.read()
            # 尝试解码
            for encoding in encodings:
                try:
                    return content.decode(encoding).strip()
                except UnicodeDecodeError:
                    continue
        
        # 最后尝试使用错误处理
        return content.decode('utf-8', errors='ignore').strip()
        
    except Exception as e:
        print(f"  错误: 无法读取文件 {file_path}: {e}")
        return None


def load_lyrics_from_directory(lyrics_dir='C:\\Lyrics', overwrite=False, dry_run=False):
    """
    从指定目录加载歌词
    
    Args:
        lyrics_dir: 歌词目录路径
        overwrite: 如果为True，覆盖已存在的歌词
        dry_run: 如果为True，只显示将要加载的歌词，不实际更新
    """
    print("=" * 60)
    print("加载歌词脚本")
    print("=" * 60)
    
    if dry_run:
        print("\n⚠️  运行模式：预览模式（不会实际更新）\n")
    else:
        print("\n⚠️  运行模式：实际更新模式\n")
    
    lyrics_path = Path(lyrics_dir)
    
    if not lyrics_path.exists():
        print(f"❌ 错误: 歌词目录不存在: {lyrics_dir}")
        return
    
    if not lyrics_path.is_dir():
        print(f"❌ 错误: 路径不是目录: {lyrics_dir}")
        return
    
    print(f"歌词目录: {lyrics_dir}\n")
    
    # 支持的歌词文件格式
    lyric_extensions = {'.txt', '.lrc', '.lyric', '.lyrics'}
    
    # 获取所有歌词文件
    lyric_files = []
    for ext in lyric_extensions:
        lyric_files.extend(lyrics_path.rglob(f'*{ext}'))
        lyric_files.extend(lyrics_path.rglob(f'*{ext.upper()}'))
    
    print(f"找到 {len(lyric_files)} 个歌词文件\n")
    
    if not lyric_files:
        print("没有找到歌词文件！")
        return
    
    # 获取所有歌曲
    all_songs = Song.objects.all()
    print(f"数据库中的歌曲数: {len(all_songs)}\n")
    
    matched_count = 0
    updated_count = 0
    skipped_count = 0
    not_found_count = 0
    
    for lyric_file in lyric_files:
        # 获取文件名（不含扩展名）
        filename_stem = lyric_file.stem
        
        print(f"处理: {lyric_file.name}")
        
        # 匹配歌曲
        matched_song = match_lyric_file_to_song(filename_stem, all_songs)
        
        if not matched_song:
            print(f"  ✗ 未找到匹配的歌曲")
            not_found_count += 1
            continue
        
        print(f"  ✓ 匹配到: {matched_song.title} - {matched_song.artist}")
        
        # 检查是否已有歌词
        if matched_song.lyrics and not overwrite:
            print(f"  ⚠️  跳过: 歌曲已有歌词（使用 --overwrite 可覆盖）")
            skipped_count += 1
            continue
        
        # 读取歌词内容
        lyrics_content = read_lyric_file(lyric_file)
        
        if not lyrics_content:
            print(f"  ✗ 无法读取歌词内容")
            continue
        
        matched_count += 1
        
        if not dry_run:
            # 更新歌词
            matched_song.lyrics = lyrics_content
            matched_song.save()
            print(f"  ✓ 已更新歌词 ({len(lyrics_content)} 字符)")
            updated_count += 1
        else:
            print(f"  ✓ 预览: 将更新歌词 ({len(lyrics_content)} 字符)")
            print(f"     歌词预览: {lyrics_content[:50]}...")
    
    print("\n" + "=" * 60)
    print("统计:")
    print(f"  处理文件数: {len(lyric_files)}")
    print(f"  成功匹配: {matched_count}")
    if not dry_run:
        print(f"  已更新: {updated_count}")
        print(f"  已跳过: {skipped_count}")
    print(f"  未找到匹配: {not_found_count}")
    print("=" * 60)
    
    if dry_run:
        print("\n提示: 这是预览模式，没有实际更新任何记录。")
        print("      如需实际更新，请运行: load_lyrics_from_directory(dry_run=False)")
        print("      如需覆盖已有歌词，请使用: --overwrite 参数")


if __name__ == '__main__':
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description='从 C:\\Lyrics 目录加载歌词到数据库',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 预览模式（默认）
  python load_lyrics.py
  
  # 实际加载歌词
  python load_lyrics.py --load
  
  # 覆盖已有歌词
  python load_lyrics.py --load --overwrite
  
  # 指定歌词目录
  python load_lyrics.py --load --dir "D:\\MyLyrics"
        '''
    )
    parser.add_argument('--load', action='store_true',
                       help='实际执行加载操作（默认是预览模式）')
    parser.add_argument('--overwrite', action='store_true',
                       help='覆盖已存在的歌词')
    parser.add_argument('--dir', type=str, default='C:\\Lyrics',
                       help='歌词目录路径（默认: C:\\Lyrics）')
    
    args = parser.parse_args()
    
    if args.load:
        print("⚠️  警告：这将更新数据库中的歌词！")
        if args.overwrite:
            print("⚠️  注意：将覆盖已存在的歌词！")
        response = input("确认继续？(yes/no): ")
        if response.lower() == 'yes':
            load_lyrics_from_directory(
                lyrics_dir=args.dir,
                overwrite=args.overwrite,
                dry_run=False
            )
        else:
            print("已取消操作")
    else:
        # 默认预览模式
        load_lyrics_from_directory(
            lyrics_dir=args.dir,
            overwrite=args.overwrite,
            dry_run=True
        )
        print("\n提示: 使用 --load 参数来实际执行加载操作")
        print("      例如: python load_lyrics.py --load")
        print("      使用 --overwrite 参数覆盖已有歌词: python load_lyrics.py --load --overwrite")

