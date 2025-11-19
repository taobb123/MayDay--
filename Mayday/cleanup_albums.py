# -*- coding: utf-8 -*-
"""
清理不属于 D:\\Music\\五月天 目录的专辑
删除所有歌曲路径都不在该目录下的专辑
"""
import os
import sys
import django
from pathlib import Path

# 设置输出编码为UTF-8
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mayday_project.settings')
django.setup()

from mayday_app.models import Album, Song

def cleanup_albums(dry_run=True):
    """
    清理不属于 D:\Music\五月天 目录的专辑
    
    Args:
        dry_run: 如果为True，只显示将要删除的专辑，不实际删除
    """
    allowed_dir = Path(r'D:\Music\五月天')
    
    print("=" * 60)
    print("清理不属于 D:\\Music\\五月天 目录的专辑")
    print("=" * 60)
    print(f"允许的目录: {allowed_dir}")
    
    if dry_run:
        print("\n[预览模式] 不会实际删除")
        print("   如需实际删除，请设置 dry_run=False\n")
    else:
        print("\n[实际删除模式]\n")
    
    # 规范化允许的目录路径
    try:
        allowed_dir_resolved = allowed_dir.resolve()
    except (OSError, RuntimeError):
        allowed_dir_resolved = allowed_dir.absolute()
    
    allowed_dir_str = str(allowed_dir_resolved)
    
    # 获取所有专辑
    all_albums = Album.objects.prefetch_related('songs').all()
    print(f"总专辑数: {all_albums.count()}\n")
    
    albums_to_delete = []
    albums_to_keep = []
    
    for album in all_albums:
        songs = album.songs.all()
        
        if not songs.exists():
            # 如果专辑没有歌曲，也标记为删除
            albums_to_delete.append((album, "无歌曲"))
            continue
        
        # 检查专辑中是否有任何歌曲在允许的目录下
        has_allowed_song = False
        song_paths = []
        
        for song in songs:
            # 检查 original_path
            if song.original_path:
                try:
                    song_path = Path(song.original_path)
                    try:
                        song_path_resolved = song_path.resolve()
                    except (OSError, RuntimeError):
                        song_path_resolved = song_path.absolute()
                    
                    song_path_str = str(song_path_resolved)
                    song_paths.append(song_path_str)
                    
                    if song_path_str.startswith(allowed_dir_str):
                        has_allowed_song = True
                        break
                except Exception as e:
                    # 如果路径解析失败，记录但不影响判断
                    pass
            
            # 也检查 file_path（上传的文件）
            if song.file_path and hasattr(song.file_path, 'path'):
                try:
                    file_path = Path(song.file_path.path)
                    try:
                        file_path_resolved = file_path.resolve()
                    except (OSError, RuntimeError):
                        file_path_resolved = file_path.absolute()
                    
                    file_path_str = str(file_path_resolved)
                    song_paths.append(file_path_str)
                    
                    if file_path_str.startswith(allowed_dir_str):
                        has_allowed_song = True
                        break
                except Exception as e:
                    pass
        
        if not has_allowed_song:
            # 如果没有任何歌曲在允许的目录下，标记为删除
            reason = f"所有 {len(songs)} 首歌曲都不在允许的目录下"
            if not song_paths:
                reason = "所有歌曲都没有文件路径"
            albums_to_delete.append((album, reason))
        else:
            albums_to_keep.append(album)
    
    # 显示结果
    print(f"将保留的专辑: {len(albums_to_keep)} 个")
    print(f"将删除的专辑: {len(albums_to_delete)} 个\n")
    
    if albums_to_delete:
        print("=" * 60)
        print("将要删除的专辑列表：")
        print("=" * 60)
        
        for album, reason in albums_to_delete:
            song_count = album.songs.count()
            print(f"\n【{album.name}】")
            print(f"  ID: {album.id}")
            print(f"  发行日期: {album.release_date}")
            print(f"  歌曲数量: {song_count}")
            print(f"  删除原因: {reason}")
            
            # 显示前3首歌曲的路径作为示例
            songs = album.songs.all()[:3]
            if songs:
                print(f"  示例歌曲路径:")
                for song in songs:
                    try:
                        path = song.original_path or (song.file_path.path if hasattr(song.file_path, 'path') else '无路径')
                        # 安全地处理路径，避免编码问题
                        title = song.title.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                        path_str = str(path).encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                        print(f"    - {title}: {path_str}")
                    except Exception as e:
                        print(f"    - {song.title}: [路径显示错误]")
        
        print("\n" + "=" * 60)
        print(f"统计:")
        print(f"  保留: {len(albums_to_keep)} 个专辑")
        print(f"  删除: {len(albums_to_delete)} 个专辑")
        
        # 统计将删除的歌曲数量
        total_songs_to_delete = sum(album.songs.count() for album, _ in albums_to_delete)
        print(f"  将删除的歌曲: {total_songs_to_delete} 首（由于专辑删除而级联删除）")
        print("=" * 60)
        
        if not dry_run:
            # 实际删除
            print("\n开始删除...")
            deleted_count = 0
            for album, reason in albums_to_delete:
                album_name = album.name
                song_count = album.songs.count()
                album.delete()
                deleted_count += 1
                print(f"[已删除] {album_name} (包含 {song_count} 首歌曲)")
            
            print(f"\n[完成] 删除完成！共删除 {deleted_count} 个专辑")
        else:
            print("\n提示: 这是预览模式，没有实际删除任何记录。")
            print("      如需实际删除，请运行: cleanup_albums(dry_run=False)")
    else:
        print("\n[完成] 没有需要删除的专辑！所有专辑都包含来自 D:\\Music\\五月天 目录的歌曲。")
    
    return albums_to_delete

if __name__ == '__main__':
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description='清理不属于 D:\\Music\\五月天 目录的专辑',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 预览模式（默认）
  python cleanup_albums.py
  
  # 实际删除
  python cleanup_albums.py --delete
        '''
    )
    parser.add_argument('--delete', action='store_true', 
                       help='实际执行删除操作（默认是预览模式）')
    
    args = parser.parse_args()
    
    if args.delete:
        print("[警告] 这将实际删除不属于 D:\\Music\\五月天 目录的专辑！")
        print("   这些专辑下的所有歌曲也会被删除（级联删除）")
        response = input("\n确认继续？(yes/no): ")
        if response.lower() == 'yes':
            cleanup_albums(dry_run=False)
        else:
            print("已取消操作")
    else:
        # 默认预览模式
        cleanup_albums(dry_run=True)

