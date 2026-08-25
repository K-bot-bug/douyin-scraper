# 抖音「喜欢」&「收藏」视频抓取工具

## 项目简介

通过 Playwright 自动化浏览器抓取个人抖音账号的「喜欢」和「收藏」视频数据，包括视频标题、播放量、点赞数、评论数、收藏数、分享数、封面图、播放链接等，支持导出 JSON 和 CSV 格式。

## 功能说明

- **自动登录**：读取 `douyin_state.json` 本地缓存的登录态，无需每次扫码
- **防检测**：集成 `playwright-stealth`，模拟真实浏览器指纹，规避自动化检测
- **双 Tab 抓取**：依次抓取「喜欢」和「收藏」两个页面
- **滚动加载**：自动向下滚动触发分页加载，直到加载完毕
- **多格式导出**：每个 Tab 分别输出 `.json` 和 `.csv` 到 `output/` 目录
- **登录态持久化**：首次登录成功后自动保存 cookie，下次免登录

## 项目结构

```
.
├── douyin_scraper.py       # 主抓取脚本
├── douyin_state.json       # 登录态缓存（Cookie/Storage），本地使用，不入仓库
├── requirements.txt        # Python 依赖
├── .env.example            # 环境变量模板（勿直接修改 .env）
├── .gitignore              # Git 忽略规则
└── output/                 # 抓取结果（不入仓库）
    ├── douyin_喜欢.json
    ├── douyin_喜欢.csv
    ├── douyin_收藏.json
    └── douyin_收藏.csv
```

## 安装

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器（首次运行一次即可）
playwright install chromium
```

## 配置账号

在项目根目录创建 `.env` 文件：

```bash
cp .env.example .env
```

编辑 `.env`，填入你的抖音手机号和密码：

```
DOUYIN_USERNAME=1xxxxxxxxx
DOUYIN_PASSWORD=your_password
```

> ⚠️ `.env` 已加入 `.gitignore`，不会上传到仓库。

## 使用方法

```bash
# 首次运行：自动打开浏览器，需手动扫码或输入密码登录
python douyin_scraper.py

# 后续运行：直接读取本地缓存的登录态，无需重新登录
python douyin_scraper.py
```

运行结束后，抓取结果保存在 `output/` 目录下。

## 输出字段说明

| 字段 | 说明 |
|------|------|
| `aweme_id` | 视频唯一 ID |
| `title` | 视频标题/描述 |
| `play_url` | 视频播放链接（无水印） |
| `cover_url` | 视频封面图链接 |
| `likes` | 点赞数 |
| `comments` | 评论数 |
| `plays` | 播放量 |
| `collects` | 收藏数 |
| `shares` | 分享数 |
| `create_time` | 发布时间（Unix 时间戳） |
| `author` | 作者昵称 |

## 注意事项

- 本工具仅用于个人数据备份和分析，请勿用于商业用途
- 首次运行需在浏览器中完成抖音登录，之后会缓存登录态
- `douyin_state.json` 包含敏感 Cookie 信息，切勿提交到公开仓库
