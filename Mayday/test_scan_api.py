"""
测试扫描API是否正常工作
"""
import os
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mayday_project.settings')
django.setup()

def test_scan_api():
    """测试扫描API"""
    print("=" * 60)
    print("测试扫描API")
    print("=" * 60)
    
    # 测试本地API
    url = 'http://localhost:8000/api/scan/'
    
    try:
        response = requests.post(
            url,
            json={},
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"响应数据: {data}")
            if data.get('status') == 'success':
                print(f"✅ 扫描成功！找到 {data.get('songs_count', 0)} 首歌曲")
            else:
                print(f"❌ 扫描失败: {data.get('message', '未知错误')}")
        elif response.status_code == 403:
            print("❌ 权限错误：API需要认证或权限不足")
        elif response.status_code == 401:
            print("❌ 认证错误：需要登录")
        else:
            print(f"❌ 请求失败: {response.status_code}")
            try:
                error_data = response.json()
                print(f"错误信息: {error_data}")
            except:
                print(f"响应内容: {response.text[:500]}")
                
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保Django服务器正在运行")
        print("   运行命令: python manage.py runserver")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 60)

if __name__ == '__main__':
    test_scan_api()

