# X (Twitter) Article Downloader

这是一个专业级的命令行工具，专为从 X (Twitter) 完整归档“文章 (Article)”和“推文 (Threads)”而设计。它不仅仅是下载文字，更能生成**高保真**的本地 HTML 副本，并自动构建可视化的知识库索引。

## 🌟 核心功能

*   **🔍 高保真抓取**：
    *   利用 Playwright 模拟真实浏览器，完美渲染动态内容。
    *   **样式注入**：自动提取并保留 X 原站的字体、排版和 CSS 样式，去除广告和侧边栏，生成干净、美观的本地 HTML。
*   **📂 智能资源管理**：
    *   **自动命名**：智能解析网页标题，生成 `作者_主题_日期` (如 `ElonMusk_Mars_2025-01-27`) 格式的文件夹。
    *   **离线化**：自动下载所有图片至 `assets/` 目录，并重写 HTML 链接，确保永久离线可读。
*   **📚 知识库构建**：
    *   **全局索引**：自动生成 `output/index.html`，以表格形式展示所有已下载文章，支持点击跳转。
    *   **元数据**：每篇文章均附带 `meta.json`，存储作者、时间、原链接等结构化数据。
*   **⚙️ 生产力特性**：
    *   **断点续传**：内置历史记录数据库，自动跳过已下载的链接（支持 `--force` 强制覆盖）。
    *   **批量处理**：支持通过 `input/urls.txt` 进行无人值守的批量下载。
    *   **双重格式**：默认生成高保真 HTML，可选生成 Markdown 格式。
        *   **Cookie 注入**：支持 JSON/Netscape 格式 Cookie，安全复用浏览器登录状态。

### 实用工具
*   **去重工具**：如果 `input/urls.txt` 中积累了大量重复链接，可以运行以下命令进行清理（保留原顺序和注释）：
    ```bash
    python3 src/clean_urls.py
    ```
*   **重建索引**：如果需要重新生成 `index.html`（例如为了更新排序或修复损坏的索引），无需重新下载文章，可运行：
    ```bash
    python3 src/regenerate_index.py
    ```

## 📂 项目结构 (模块化架构)

```text
.
├── src/
│   ├── templates/       # [视图层] Jinja2 HTML 模板
│   ├── config.py        # [配置层] 环境变量加载
│   ├── main.py          # [控制层] CLI入口与流程调度
│   ├── extractor.py     # [业务层] HTML解析、元数据提取、样式清洗
│   ├── downloader.py    # [服务层] 资源下载与文件保存 (集成在 main 中)
│   ├── indexer.py       # [索引层] 扫描本地库并生成 index.html
│   ├── exporter.py      # [导出层] PDF与EPUB格式转换逻辑
│   ├── history.py       # [持久层] 下载记录管理
│   ├── utils.py         # [工具层] 文件名清洗、Cookie加载
│   └── logger.py        # [日志层] 全局日志配置
├── input/
│   ├── cookies.txt      # (自备) 导出的 Cookie 文件
│   └── urls.txt         # (自备) 批量下载列表
├── .env                 # (推荐) 全局配置文件
├── output/              # 结果目录 (按 "作者_主题_日期" 分类)
│   ├── index.html       # 全局文章索引页 (支持分页)
│   └── ...              # 各文章文件夹
├── logs/                # 运行日志
├── run.sh               # 一键启动脚本
└── requirements.txt     # 依赖列表
```

## ⚙️ 配置说明 (.env)

项目支持通过 `.env` 文件进行无代码配置（推荐）：

```ini
# --- 核心行为 ---
DEFAULT_TIMEOUT=20       # 页面加载超时 (秒)
DEFAULT_SCROLL_COUNT=5   # 向下滚动次数
MAX_WORKERS=8            # 并行下载线程数
ITEMS_PER_PAGE=20        # 索引页每页显示文章数

# --- 选择器配置 (适应 X 平台变动) ---
SELECTOR_ARTICLE="article"
# ...
```

## 🚀 快速开始

### 1. 初始化
确保系统已安装 Python 3.8+。首次运行将自动创建虚拟环境并安装依赖：

```bash
chmod +x run.sh
./run.sh --help
```

### 3. 准备 Cookie

### 2. 准备 Cookie
X (Twitter) 必须登录才能查看完整内容。
1.  在浏览器登录 [x.com](https://x.com)。
2.  使用插件（如 **Get cookies.txt LOCALLY**）导出 Cookie。
3.  保存为 `input/cookies.txt` (支持 Netscape 格式或 JSON)。

### 3. 运行下载

**单条下载：**
```bash
./run.sh "https://x.com/username/status/123456"
```

**批量下载：**
将链接写入 `input/urls.txt` (每行一个)，然后运行：
```bash
./run.sh input/urls.txt
```

**导出为 PDF/EPUB：**
```bash
./run.sh input/urls.txt --pdf --epub
```

## ⚙️ 参数详解

| 参数 | 说明 | 默认值 |
| :--- | :--- | :--- |
| `input` | 单个 URL 或包含 URL 的文件路径 | (必填) |
| `--markdown` | 开启 Markdown 格式导出 | False |
| `--pdf` | 导出为 PDF 格式 | False |
| `--epub` | 导出为 EPUB 电子书格式 | False |
| `--scroll N` | 自动向下滚动 N 次以加载懒加载图片 | 5 |
| `--timeout N` | 页面加载超时时间 (秒) | 20 |
| `--headless` | 显示浏览器窗口 (用于调试验证码或登录) | False (默认静默运行) |
| `--force` | 忽略历史记录，强制重新下载 | False |
| `--output` | 指定输出根目录 | `output/` |

## 🛠️ 常见问题

*   **Q: 为什么生成的文件夹是 URL 乱码？**
    *   A: 这通常意味着元数据提取失败（可能是因为页面未完全加载）。尝试增加 `--timeout 30` 或 `--scroll 10`。
*   **Q: 怎么看下载进度？**
    *   A: 查看终端输出，或检查 `logs/` 目录下的最新日志文件。
*   **Q: 下载中断了怎么办？**
    *   A: 直接重新运行命令即可。程序会自动识别 `logs/downloaded_history.txt`，跳过已完成的任务。

## 🗓️ 路线图 (Roadmap)
查看 [docs/ROADMAP.md](docs/ROADMAP.md) 了解未来的功能规划与改进建议。