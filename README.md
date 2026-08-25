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

## 项目实现

### 整体架构

```
DouyinScraper（主控制器）
├── launch()          浏览器初始化 + 反检测配置
├── login()           账号密码登录 + 登录态持久化
├── scrape_tab()      单 Tab 数据抓取（监听 API 响应）
│   ├── 监听 response 事件
│   ├── 滚动加载触发分页
│   └── 解析 JSON 提取字段
└── export_results()  数据导出（JSON + CSV）
```

### 核心实现细节

**1. 浏览器初始化与反检测（launch）**
- 使用 Playwright 启动可见 Chromium，关闭 headless 模式
- 注入 `--disable-blink-features=AutomationControlled` 屏蔽自动化标记
- 调用 `playwright_stealth.Stealth()` 重写 `navigator.webdriver`、`chrome.runtime` 等检测特征
- 加载 `douyin_state.json` 中的已缓存 Cookie，跳过首次登录流程

**2. 登录态管理（login）**
- 导航至 `/user/self` 触发登录弹窗
- 通过 JS 定位「密码登录」按钮并点击（兼容抖音 DOM 动态变化）
- 自动填写账号密码后提交，检测页面是否含「未登录」字样判断登录结果
- 登录成功后调用 `storage_state()` 序列化全部 Cookie 和本地存储，保存至 `douyin_state.json`

**3. 数据抓取与去重（scrape_tab）**
- **监听网络响应**：注册 `page.on("response")` 回调，拦截包含 `aweme` 或 `feed` 的 API 请求
- **JSON 解析**：从响应体中提取 `aweme_list` 数组，读取每个视频的统计数据字段
- **去重机制**：维护 `seen_ids` 集合（`aweme_id`），已收录的条目直接跳过
- **滚动加载策略**：
  - 每次滚动 2000px，等待 2s 触发懒加载
  - 连续 5 次 `scrollHeight` 无变化则判定加载完毕
  - 最多滚动 100 次防止死循环
  - 到达页面底部时提前终止

**4. 数据导出（export_results）**
- **JSON 格式**：保留完整字段，含元数据（抓取时间、Tab 名称、总数）
- **CSV 格式**：使用 `utf-8-sig` 编码（Excel 原生支持中文），列出 11 个常用字段

### 技术难点与解决

| 问题 | 解决方案 |
|------|---------|
| 抖音检测自动化脚本 | playwright-stealth + navigator.webdriver 覆写 |
| 登录弹窗元素定位不稳定 | JS querySelectorAll 遍历匹配文本「密码登录」 |
| 页面滚动到底部后仍加载 | scrollHeight 连续 5 次无变化作为终止条件 |
| 视频 ID 重复抓取 | seen_ids 集合去重 |
| 账号密码硬编码风险 | dotenv 环境变量配置，.env 加入 .gitignore |

### 依赖说明

| 库 | 用途 |
|----|------|
| playwright | 浏览器自动化，控制 Chromium 完成登录和滚动 |
| playwright-stealth | 消除浏览器自动化特征，绕过平台检测 |
| python-dotenv | 从 .env 文件读取账号密码，避免硬编码 |

---

## 注意事项

- 本工具仅用于个人数据备份和分析，请勿用于商业用途
- 首次运行需在浏览器中完成抖音登录，之后会缓存登录态
- `douyin_state.json` 包含敏感 Cookie 信息，切勿提交到公开仓库
