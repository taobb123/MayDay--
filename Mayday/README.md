# 五月天音乐收藏系统

一个基于Django的五月天音乐收藏整理系统，支持文件扫描、音乐播放、专辑时间线和相册功能。

## 功能特性

- 🎵 **音乐扫描**：自动扫描 `D:\Music\五月天` 目录，提取音频文件元数据
- 🎶 **音乐播放**：内置音乐播放器，支持在线播放
- 📅 **时间隧道**：以专辑时间线为主线，整合专辑、巡回演出、言论、图片等内容
- 🖼️ **相册功能**：支持图片上传和展示
- 🎨 **美观UI**：现代化的响应式界面设计

## 技术架构

### 框架
- **Django 4.2+**：Web框架
- **Django REST Framework**：API框架

### 设计模式
- **接口编程**：使用抽象基类定义接口（`interfaces.py`）
- **组合优于继承**：使用对象组合实现功能复用
- **代理模式**：`MusicScannerProxy`、`MessageQueueProxy`
- **委托模式**：消息队列和扫描器的委托实现
- **分层技术**：清晰的接口层、实现层、数据层分离

### 组件
- **Kafka**（可选）：消息队列，支持异步任务处理
- **Mutagen**：音频文件元数据提取
- **Pillow**：图片处理

## 项目结构

```
Mayday/
├── mayday_project/          # Django项目配置
│   ├── settings.py          # 项目设置
│   ├── urls.py              # URL路由
│   └── ...
├── mayday_app/              # 主应用
│   ├── interfaces.py        # 抽象接口定义
│   ├── models.py            # 数据模型
│   ├── scanner.py           # 文件扫描模块（代理模式）
│   ├── timeline.py          # 时间线模块（组合模式）
│   ├── messaging.py         # 消息队列模块（代理模式）
│   ├── views.py             # 视图
│   ├── serializers.py       # API序列化器
│   └── ...
├── templates/               # 前端模板
│   └── mayday_app/
│       ├── base.html
│       ├── index.html
│       └── album_detail.html
└── requirements.txt         # 依赖包
```

## 安装和运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置设置

编辑 `mayday_project/settings.py`，修改音乐目录路径：

```python
MUSIC_DIRECTORY = r'D:\Music\五月天'  # 修改为你的音乐目录
```

### 3. 数据库迁移

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. 创建超级用户（可选）

```bash
python manage.py createsuperuser
```

### 5. 运行开发服务器

```bash
python manage.py runserver
```

访问 http://127.0.0.1:8000

## 使用说明

### 扫描音乐

1. 点击首页的"扫描音乐"按钮
2. 系统会自动扫描配置的音乐目录
3. 提取音频文件的元数据（标题、艺术家、专辑等）
4. 自动创建专辑和歌曲记录

### 浏览时间线

时间线页面展示所有内容按时间排序：
- 专辑（蓝色标记）
- 巡回演出（黄色标记）
- 言论（绿色标记）
- 图片（红色标记）

### 播放音乐

在歌曲列表中点击"播放"按钮，底部会弹出音乐播放器。

### 管理后台

访问 http://127.0.0.1:8000/admin 可以：
- 管理专辑、歌曲、巡回演出、言论、图片
- 手动添加和编辑内容

## API接口

- `GET /api/albums/` - 获取专辑列表
- `GET /api/songs/` - 获取歌曲列表
- `GET /api/timeline/` - 获取时间线数据
- `POST /api/scan/` - 触发音乐扫描

## 设计模式说明

### 接口编程
所有核心功能都定义了接口（`interfaces.py`），实现类遵循接口契约，便于扩展和测试。

### 组合优于继承
- `TimelineRepository` 使用组合整合不同类型的模型
- 避免深度继承层次，提高灵活性

### 代理模式
- `MusicScannerProxy`：为扫描器添加缓存功能
- `MessageQueueProxy`：根据配置选择Kafka或本地队列

### 委托模式
- 消息队列委托给Kafka或本地实现
- 扫描器委托给mutagen库处理不同格式

## 扩展性

系统设计支持轻松扩展：
- 添加新的时间线项目类型：实现 `TimeTunnelItem` 接口
- 添加新的音频格式支持：扩展 `MusicScanner` 的格式列表
- 替换消息队列：实现 `MessageQueueInterface` 接口

## 注意事项

1. **文件路径**：确保音乐目录路径正确配置
2. **Kafka**：默认禁用，如需使用请配置Kafka并设置 `KAFKA_ENABLED = True`
3. **媒体文件**：上传的图片和音频文件存储在 `media/` 目录

## 许可证

MIT License

