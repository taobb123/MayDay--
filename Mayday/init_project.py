"""
项目初始化脚本
运行此脚本来初始化数据库和创建必要的目录
"""
import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mayday_project.settings')
django.setup()

from django.core.management import execute_from_command_line

if __name__ == '__main__':
    print("=" * 50)
    print("五月天音乐收藏系统 - 项目初始化")
    print("=" * 50)
    
    # 创建必要的目录
    directories = ['static', 'media', 'media/albums', 'media/songs', 'media/images']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ 创建目录: {directory}")
    
    # 运行数据库迁移
    print("\n运行数据库迁移...")
    execute_from_command_line(['manage.py', 'makemigrations'])
    execute_from_command_line(['manage.py', 'migrate'])
    
    print("\n" + "=" * 50)
    print("初始化完成！")
    print("=" * 50)
    print("\n下一步：")
    print("1. 确保音乐目录路径正确配置在 settings.py 中")
    print("2. 运行: python manage.py runserver")
    print("3. 访问: http://127.0.0.1:8000")
    print("4. 点击'扫描音乐'按钮开始扫描音乐文件")

