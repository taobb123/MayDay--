"""
填充所有歌曲的拼音字段
运行方式: python populate_pinyin.py
"""
import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mayday_project.settings')
django.setup()

from mayday_app.models import Song

def populate_pinyin_fields():
    """填充所有歌曲的拼音字段"""
    try:
        from pypinyin import lazy_pinyin, Style
        
        # 获取所有不重复的歌手
        artists = Song.objects.values_list('artist', flat=True).distinct()
        
        print(f"找到 {len(artists)} 个不同的歌手")
        
        updated_count = 0
        for artist in artists:
            if not artist:
                continue
            
            # 生成拼音
            pinyin_list = lazy_pinyin(artist, style=Style.NORMAL)
            pinyin = ''.join(pinyin_list)
            
            # 获取首字母（取第一个字符的拼音首字母）
            if pinyin:
                initial = pinyin[0].upper()
            else:
                # 如果是英文，直接取首字母
                initial = artist[0].upper() if artist else ''
            
            # 确保首字母是A-Z
            if initial and initial.isalpha() and initial.isascii():
                initial = initial.upper()
            else:
                # 如果不是字母，归类到"#"
                initial = '#'
            
            # 更新所有该歌手的歌曲
            songs_updated = Song.objects.filter(artist=artist).update(
                artist_pinyin=pinyin,
                artist_initial=initial
            )
            
            if songs_updated > 0:
                updated_count += songs_updated
                print(f"✓ {artist}: 拼音={pinyin}, 首字母={initial}, 更新了 {songs_updated} 首歌曲")
        
        print(f"\n完成！共更新 {updated_count} 首歌曲的拼音字段")
        
    except ImportError:
        print("错误: pypinyin 未安装，请先运行: pip install pypinyin")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    populate_pinyin_fields()

