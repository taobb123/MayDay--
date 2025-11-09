"""
清理重复歌曲脚本
删除基于标题、艺术家和专辑的重复歌曲记录，保留最完整的那一条
"""
import os
import django
from collections import defaultdict

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mayday_project.settings')
django.setup()

from django.db.models import Q
from mayday_app.models import Song, Album


def cleanup_duplicate_songs(dry_run=True, exclude_ids=None):
    """
    清理重复的歌曲记录
    
    Args:
        dry_run: 如果为True，只显示将要删除的记录，不实际删除
        exclude_ids: 要排除的歌曲ID列表（这些ID不会被删除）
    """
    print("=" * 60)
    print("清理重复歌曲脚本")
    print("=" * 60)
    
    if dry_run:
        print("\n⚠️  运行模式：预览模式（不会实际删除）")
        print("   如需实际删除，请设置 dry_run=False\n")
    else:
        print("\n⚠️  运行模式：实际删除模式\n")
    
    # 处理排除的ID
    exclude_ids_set = set()
    if exclude_ids:
        exclude_ids_set = set(int(id) for id in exclude_ids)
        if exclude_ids_set:
            print(f"📌 排除的歌曲ID: {sorted(exclude_ids_set)}\n")
    
    # 获取所有歌曲
    all_songs = Song.objects.all()
    print(f"总歌曲数: {len(all_songs)}")
    
    # 按标题、艺术家和专辑分组
    song_groups = defaultdict(list)
    
    for song in all_songs:
        # 创建唯一键：标题 + 艺术家 + 专辑ID
        album_id = song.album.id if song.album else None
        key = (song.title.strip(), song.artist.strip(), album_id)
        song_groups[key].append(song)
    
    # 找出重复的组
    duplicate_groups = {k: v for k, v in song_groups.items() if len(v) > 1}
    
    if not duplicate_groups:
        print("\n✓ 没有发现重复歌曲！")
        return
    
    print(f"\n发现 {len(duplicate_groups)} 组重复歌曲：\n")
    
    total_to_delete = 0
    total_kept = 0
    
    for (title, artist, album_id), songs in duplicate_groups.items():
        album_name = songs[0].album.name if songs[0].album else "无专辑"
        print(f"\n【{title} - {artist}】({album_name})")
        print(f"  重复数量: {len(songs)} 条")
        
        # 选择要保留的歌曲（保留最完整的那一条）
        # 优先级：1. 有original_path的 2. 有file_path的 3. 有更多信息的 4. 最早创建的
        def get_priority(song):
            score = 0
            if song.original_path:
                score += 1000
            if song.file_path:
                score += 500
            if song.duration:
                score += 100
            if song.track_number:
                score += 50
            if song.lyrics:
                score += 10
            # 创建时间越早，分数越高（保留最早的）
            score += (song.created_at.timestamp() if song.created_at else 0) / 1000000
            return score
        
        # 按优先级排序
        sorted_songs = sorted(songs, key=get_priority, reverse=True)
        
        # 如果最高优先级的歌曲在排除列表中，选择下一个
        song_to_keep = None
        for song in sorted_songs:
            if song.id not in exclude_ids_set:
                song_to_keep = song
                break
        
        # 如果所有歌曲都在排除列表中，保留优先级最高的
        if song_to_keep is None:
            song_to_keep = sorted_songs[0]
            print(f"  ⚠️  注意：所有记录都在排除列表中，保留优先级最高的")
        
        songs_to_delete = [s for s in sorted_songs if s.id != song_to_keep.id]
        
        # 标记是否被排除
        keep_marker = "🔒" if song_to_keep.id in exclude_ids_set else "✓"
        print(f"  {keep_marker} 保留: ID={song_to_keep.id}, 路径={song_to_keep.original_path or song_to_keep.file_path or '无'}")
        
        excluded_count = 0
        for song in songs_to_delete:
            if song.id in exclude_ids_set:
                excluded_count += 1
                print(f"  🔒 排除（不删除）: ID={song.id}, 路径={song.original_path or song.file_path or '无'}")
            else:
                total_to_delete += 1
                print(f"  ✗ 删除: ID={song.id}, 路径={song.original_path or song.file_path or '无'}")
                if not dry_run:
                    song.delete()
        
        if excluded_count > 0:
            print(f"    本组有 {excluded_count} 条记录被排除，不会删除")
        
        total_kept += 1
    
    print("\n" + "=" * 60)
    print(f"统计:")
    print(f"  保留: {total_kept} 组（每组保留1条）")
    print(f"  删除: {total_to_delete} 条重复记录")
    if exclude_ids_set:
        excluded_songs = Song.objects.filter(id__in=exclude_ids_set).count()
        print(f"  排除: {excluded_songs} 条记录（在排除列表中）")
    print(f"  剩余: {len(all_songs) - total_to_delete} 条歌曲")
    print("=" * 60)
    
    if dry_run:
        print("\n提示: 这是预览模式，没有实际删除任何记录。")
        print("      如需实际删除，请运行: cleanup_duplicate_songs(dry_run=False)")


def cleanup_empty_path_songs(dry_run=True):
    """
    清理没有文件路径的歌曲（可选）
    
    Args:
        dry_run: 如果为True，只显示将要删除的记录，不实际删除
    """
    print("\n" + "=" * 60)
    print("清理无文件路径的歌曲")
    print("=" * 60)
    
    if dry_run:
        print("\n⚠️  运行模式：预览模式（不会实际删除）\n")
    else:
        print("\n⚠️  运行模式：实际删除模式\n")
    
    # 查找既没有original_path也没有file_path的歌曲
    empty_songs = Song.objects.filter(
        Q(original_path='') | Q(original_path__isnull=True),
        Q(file_path__isnull=True) | Q(file_path='')
    )
    
    count = empty_songs.count()
    
    if count == 0:
        print("✓ 没有发现无文件路径的歌曲！")
        return
    
    print(f"发现 {count} 首无文件路径的歌曲：\n")
    
    for song in empty_songs[:10]:  # 只显示前10条
        album_name = song.album.name if song.album else "无专辑"
        print(f"  - {song.title} - {song.artist} ({album_name})")
    
    if count > 10:
        print(f"  ... 还有 {count - 10} 首")
    
    if not dry_run:
        deleted_count = empty_songs.delete()[0]
        print(f"\n✓ 已删除 {deleted_count} 首无文件路径的歌曲")
    else:
        print(f"\n提示: 这是预览模式，没有实际删除任何记录。")


if __name__ == '__main__':
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description='清理重复歌曲脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 预览模式（默认）
  python cleanup_duplicate_songs.py
  
  # 实际删除
  python cleanup_duplicate_songs.py --delete
  
  # 删除时排除指定ID
  python cleanup_duplicate_songs.py --delete --exclude 123 456 789
        '''
    )
    parser.add_argument('--delete', action='store_true', 
                       help='实际执行删除操作（默认是预览模式）')
    parser.add_argument('--exclude', nargs='+', type=int, metavar='ID',
                       help='要排除的歌曲ID列表（这些ID不会被删除），可以指定多个，用空格分隔')
    
    args = parser.parse_args()
    
    if args.delete:
        print("⚠️  警告：这将实际删除重复的歌曲记录！")
        if args.exclude:
            print(f"📌 排除的歌曲ID: {args.exclude}")
        response = input("确认继续？(yes/no): ")
        if response.lower() == 'yes':
            cleanup_duplicate_songs(dry_run=False, exclude_ids=args.exclude)
            print("\n是否也清理无文件路径的歌曲？")
            response2 = input("(yes/no): ")
            if response2.lower() == 'yes':
                cleanup_empty_path_songs(dry_run=False)
        else:
            print("已取消操作")
    else:
        # 默认预览模式
        exclude_ids = args.exclude if args.exclude else None
        cleanup_duplicate_songs(dry_run=True, exclude_ids=exclude_ids)
        print("\n")
        cleanup_empty_path_songs(dry_run=True)
        print("\n提示: 使用 --delete 参数来实际执行删除操作")
        print("      例如: python cleanup_duplicate_songs.py --delete")
        print("      使用 --exclude 参数排除指定ID: python cleanup_duplicate_songs.py --delete --exclude 123 456")

