# 通用文章下载器 (Universal Article Downloader)

一款基于 Playwright 和 Python 的高保真、插件化内容归档工具。旨在完整捕捉动态网页（如 X.com）的原始状态，实现离线保存。

## 🚀 核心特性

*   **插件化架构**: 易于扩展以支持新平台（当前深度支持 X.com/Twitter）。
*   **高保真归档**: 完整抓取原始 HTML、CSS 和图片，不使用会破坏排版的“阅读模式”。
*   **Twitter 长文章支持**: 专门针对 Twitter Articles（长文章）优化了内容提取逻辑。
*   **抗波动能力**: 内置重试机制，处理网络波动及滚动加载内容。
*   **原子化数据安全**: 稳健的 CSV 数据库管理，支持目录自动同步，防止记录丢失。
*   **高度可配置**: 所有选择器和行为均可在 `config.yaml` 中灵活定义。
*   **多格式导出**: 支持导出为 HTML、Markdown、PDF 和 EPUB。

## 🛠️ 安装指南

1.  **克隆并设置**:
    ```bash
    git clone <repo_url>
    cd X_download_article
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    playwright install chromium
    ```

2.  **配置说明**:
    系统通过 `config.yaml` 进行设置。您可以在其中调整超时时间、滚动次数或 CSS 选择器。
    
    **注意**: 如需访问受限内容，请将您的浏览器 Cookies（Netscape 或 JSON 格式）保存至 `input/cookies.txt`。

## 🏃 使用说明

### 基础下载
```bash
# 下载单个 URL 并生成 Markdown
python3 src/main.py "https://x.com/username/status/123456789" --markdown

# 从文件批量下载
python3 src/main.py input/urls.txt --markdown --pdf
```

### 常用参数
*   `--markdown`: 生成 Markdown 版本。
*   `--pdf`: 生成 PDF 版本。
*   `--epub`: 生成 EPUB 电子书。
*   `--scroll 5`: 针对动态内容向下滚动的次数。
*   `--force`: 强制重新下载（即使记录中已存在）。
*   `--timeout 30`: 设置自定义超时时间（秒）。

#### 什么时候需要调整 `--scroll`？
在以下场景中建议增加滚动次数：
*   **长推文串**: 捕捉 X 上的深度回复和完整对话。
*   **无限加载流**: 从用户主页或搜索结果中获取更多内容。
*   **图片懒加载**: 确保触发并捕捉初始视图之外的图片。
*   **建议**: 普通推文使用 `5`，深度讨论建议使用 `10-20`。

### 系统维护
*   **同步记录**: 手动删除文件后，同步数据库：
    ```bash
    python3 src/helper.py sync
    ```
*   **查看统计**: 查看当前下载摘要：
    ```bash
    python3 src/helper.py stats
    ```

## 🧪 测试与调试

### 质量保证
运行完整测试套件以确保系统稳定性：
```bash
./test.sh
```
这将运行单元测试和集成测试，并生成覆盖率报告。

### 诊断与调试
*   **网页加载诊断**: 如果抓取失败，查看浏览器真实所见（保存截图和 HTML）：
    ```bash
    python3 src/diagnose_url.py "https://x.com/..." --times 1
    ```
*   **提取逻辑调试**: 使用保存的 HTML 离线测试提取逻辑：
    ```bash
    python3 src/debug_extractor.py path/to/saved.html --url "https://x.com/..."
    ```

**项目结构:**
*   `src/plugins/`: 平台特定逻辑（如 `x_com.py`）。
*   `src/main.py`: 核心调度程序。
*   `config.yaml`: 全局配置文件。
*   [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md): 详细的目录与模块指南。
*   [USAGE_GUIDE.md](USAGE_GUIDE.md): 完整的使用与故障排除指南。

## 📝 许可证
MIT