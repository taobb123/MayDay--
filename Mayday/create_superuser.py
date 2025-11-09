"""
创建Django超级用户脚本
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mayday_project.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# 默认用户名和密码
username = 'admin'
password = 'admin123'
email = 'admin@mayday.com'

# 检查用户是否已存在
if User.objects.filter(username=username).exists():
    print(f'用户 "{username}" 已存在')
    user = User.objects.get(username=username)
    # 重置密码
    user.set_password(password)
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print(f'已更新用户 "{username}" 的密码')
else:
    # 创建新用户
    User.objects.create_superuser(
        username=username,
        email=email,
        password=password
    )
    print(f'已创建超级用户: {username}')

print(f'\n登录信息:')
print(f'  用户名: {username}')
print(f'  密码: {password}')
print(f'\n请登录后立即修改密码！')

