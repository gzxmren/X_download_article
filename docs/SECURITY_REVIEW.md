# 安全与可靠性评估报告 (Security & Reliability Review)

**日期**: 2026-02-07
**评估版本**: v1.0

---

## 1. 总体评价
本程序 (`X_download_article`) 架构清晰，采用了插件化设计。在代码实现上展现了良好的工程实践，如：
- **配置分离**: 使用 `config.yaml` 管理 CSS 选择器。
- **原子性操作**: `RecordManager` 在写入数据时使用临时文件交换，防止崩溃导致数据损坏。
- **健壮性**: 使用 `tenacity` 库处理网络重试。
- **隐私**: `.gitignore` 包含敏感信息（Cookies/Output）。

---

## 2. 安全隐患分析 (Security Risks)

### 🚨 2.1 SSRF 与 本地文件泄露 (High Risk)
*   **问题描述**: `XComPlugin.can_handle` 方法仅通过 `in url` 检查关键词，验证过于宽松。
*   **潜在威胁**:
    - **LFI (本地文件包含)**: 输入 `file:///etc/passwd?domain=x.com` 可绕过检查并导致本地文件内容被读取。
    - **SSRF**: 攻击者可利用程序请求内网敏感接口。
*   **改进建议**: 使用 `urllib.parse.urlparse` 严格校验 `scheme` (http/https) 和 `netloc` (域名)。

### ⚠️ 2.2 路径遍历与文件名注入 (Medium Risk)
*   **问题描述**: `sanitize_filename` 虽过滤了路径分隔符，但未处理 Null Byte (`\0`)、控制字符及特定保留文件名（如 `..`）。
*   **潜在威胁**: 
    - 恶意标题可能导致文件名异常或程序崩溃 (DoS)。
    - 虽然当前的命名格式（包含日期和作者）降低了该风险，但仍不具备完全的鲁棒性。
*   **改进建议**: 移除 0x00-0x1f 控制字符，禁止文件名以 `.` 开头。

### ⚠️ 2.3 CSV 注入 (Medium Risk)
*   **问题描述**: `RecordManager` 直接将网页内容（标题、作者）写入 CSV。
*   **潜在威胁**: 若标题以 `=`, `+`, `-`, `@` 开头，Excel 等工具打开时会执行公式，可能导致远程代码执行 (RCE) 或信息泄露。
*   **改进建议**: 对以特殊符号开头的单元格内容进行转义（如添加前缀单引号 `'`）。

### ℹ️ 2.4 内容安全 (Low Risk)
*   **问题描述**: 下载的 HTML 被清洗后渲染。
*   **潜在威胁**: 虽然移除了 `<script>`，但若清洗不彻底（如保留了 `javascript:` 伪协议的链接或未处理 `autoescape`），可能存在 Stored XSS 风险。
*   **改进建议**: 在渲染时强制启用 Jinja2 的 HTML 转义，或使用更严格的清洗库。

---

## 3. 可靠性评估 (Reliability Analysis)

### 3.1 导航等待策略
*   **现状**: 使用硬编码的 `time.sleep(3)`。
*   **改进**: 建议使用 `page.wait_for_load_state('networkidle')`，能同时兼顾速度与稳定性。

### 3.2 资源下载限制
*   **现状**: 图片下载无大小限制。
*   **改进**: 增加 `Content-Length` 检查，防止下载超大文件或“解压炸弹”导致磁盘空间耗尽。

---

## 4. 改进路线图 (Action Plan)

1.  **Phase 1 (Immediate)**: 修复 `can_handle` URL 验证逻辑。
2.  **Phase 2 (Hardening)**: 增强文件名清洗函数，添加 CSV 注入防御。
3.  **Phase 3 (Optimization)**: 优化 Playwright 等待机制，移除 `time.sleep`。
