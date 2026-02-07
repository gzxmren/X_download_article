# X-Download-Article 使用与调试指南

本文档详细说明了项目中各类程序的调用方式、运行目的及常用参数，帮助您快速上手并进行故障排除。

---

## 1. 核心执行程序 (Core Executables)

### A. 全能下载器 (`src/main.py`)
*   **目的**：执行网页抓取、内容提取及文件生成。
*   **调用方式**：
    ```bash
    # 方式 1：交互式输入 (推荐用于复杂 URL)
    python3 src/main.py
    # 按提示粘贴 URL 即可，无需担心引号转义问题
    
    # 方式 2：下载单个 URL (命令行参数)
    python3 src/main.py "https://x.com/user/status/123" --markdown
    
    # 方式 3：批量下载
    python3 src/main.py input/urls.txt --markdown --pdf
    ```
*   **常用参数**：
    *   `--markdown`: 生成 `.md` 格式文件。
    *   `--pdf`: 生成 `.pdf` 格式文件（需 Playwright 环境）。
    *   `--epub`: 生成 `.epub` 电子书。
    *   `--force`: 即使记录显示已下载，也强制重新执行。
    *   `--timeout [秒]`: 设置页面加载超时时间（默认 30s）。

### B. 记录管理器 (`src/helper.py`)
*   **目的**：管理 `records.csv` 数据库，确保下载状态与本地文件同步。
*   **子命令**：
    *   **同步索引**：根据 `output/` 目录下的实际文件夹重新生成 `records.csv`。
        ```bash
        python3 src/helper.py sync
        ```
    *   **查看统计**：显示当前下载成功与失败的总数。
        ```bash
        python3 src/helper.py stats
        ```
    *   **导出 URL**：将已成功的链接提取到文件。
        ```bash
        python3 src/helper.py export --status success exported_list.txt
        ```

---

## 2. 检测与调试程序 (Diagnostics & Debugging)

### A. 网页加载诊断 (`src/diagnose_url.py`)
*   **目的**：当某个页面抓取失败时，通过此工具查看浏览器加载后的真实状态。
*   **调用方式**：
    ```bash
    python3 src/diagnose_url.py "https://x.com/problematic_url" --times 1
    ```
*   **产出**：在 `output/debug/` 下生成 `.png` 截图和 `.html` 源码。

### B. 提取逻辑调试 (`src/debug_extractor.py`)
*   **目的**：离线测试 CSS 选择器或正则逻辑，无需重新下载网页。
*   **调用方式**：
    ```bash
    python3 src/debug_extractor.py output/debug/saved_page.html --url "https://x.com/xxx"
    ```

### C. URL 清洗工具 (`src/clean_urls.py`)
*   **目的**：自动清理 `input/urls.txt` 中的重复链接和冗余参数。
*   **调用方式**：
    ```bash
    python3 src/clean_urls.py input/urls.txt
    ```

---

## 3. 测试程序 (Testing)

### A. 全自动化测试 (`test.sh`)
*   **目的**：运行所有 pytest 用例，确保核心逻辑（如文件名清洗、配置加载）正常。
*   **调用方式**：
    ```bash
    ./test.sh
    ```

### B. 细粒度测试 (`pytest`)
*   **调用方式**：
    ```bash
    # 仅测试工具类
    pytest tests/unit/test_utils.py
    ```

---

## 3. 索引页面功能 (Index Page Features)

下载完成后生成的 `output/index.html` 是您的个人文章库门户，支持以下交互功能：

*   **实时搜索**：在搜索框输入关键字，列表将实时过滤，仅显示匹配标题、作者或日期的条目。
*   **关键字高亮**：搜索匹配到的文本会以黄色背景高亮显示，方便快速定位。
*   **动态排序**：点击表头（Date, Topic, Author）或使用顶部的排序按钮，可对文章进行升序或降序排列。
*   **离线性能**：所有数据已嵌入 HTML，搜索和排序均在本地浏览器内存中完成，响应速度极快且无需网络。

---

## 4. 推荐日常工作流 (Recommended Workflow)

1.  **准备**：将新链接写入 `input/urls.txt`。
2.  **执行**：运行 `python3 src/main.py input/urls.txt --markdown`。
3.  **排查**：若某链接报错，运行 `src/diagnose_url.py` 观察截图。
4.  **修复**：若选择器失效，修改 `config.yaml` 并在 `src/debug_extractor.py` 中验证。
5.  **测试**：修改代码后，运行 `./test.sh` 确保系统依然稳定。
6.  **维护**：定期运行 `src/helper.py sync` 保持数据库整洁。
7.  **清理**：若需删除某文章，请参考下文的“删除流程”。

---

## 5. 如何删除已下载的文章 (Data Consistency)

为了保持磁盘文件、下载记录（`records.csv`）和网页索引（`index.html`）的一致性，请遵循以下流程：

1.  **物理删除**：
    在 `output/` 目录下删除该文章对应的整个文件夹。
    ```bash
    rm -rf output/作者名_文章标题_ID_日期/
    ```

2.  **同步记录**：
    运行同步命令。该工具会自动识别已删除的文件夹，并从 `records.csv` 中移除对应的记录。
    ```bash
    python3 src/helper.py sync
    ```

3.  **更新索引**：
    执行一次下载任务（或带空参数运行 `python3 src/main.py --force ""`），程序会自动重新生成 `output/index.html`，从而移除已删除文章的链接。
