

---

## 7. URL 下载状态判断机制 (v2.4.0)

程序通过一个专门的记录系统来判断一篇文章是否已经下载过，从而避免重复工作，这个机制是保证程序高效、可重复运行的关键。

整个判断流程如下：

### **第一步：启动时加载历史记录**

1.  当程序（`XDownloader`）初始化时，它会创建一个 `RecordManager` 的实例 (`src/record_manager.py`)。
2.  `RecordManager` 在初始化时，会立即读取 `output/records.csv` 文件。
3.  它将 `records.csv` 中的每一行数据加载到内存中，并构建一个以 **URL 为键 (key)** 的字典。这个内存中的字典就像一个快速查询的缓存，存储了所有已处理过的 URL 及其下载状态。

### **第二步：处理前进行检查**

1.  在对每个 URL 执行任何耗时的网络操作（如浏览器导航、下载图片）**之前**，程序会首先调用 `RecordManager` 的 `is_downloaded(url)` 方法。
2.  `is_downloaded` 方法会拿着传入的 `url`，去第一步加载到内存的字典中进行查询。

### **第三步：根据查询结果决策**

*   **如果 URL 存在于记录中，并且状态为 `success`**：
    *   `is_downloaded()` 方法会返回 `True`。
    *   `XDownloader` 收到这个信号后，会立即跳过该 URL 的处理，并打印一条 `⏭️ Skipping already downloaded: ...` 的日志。

*   **如果 URL 不在记录中，或记录的状态为 `failed`**：
    *   `is_downloaded()` 方法会返回 `False`。
    *   `XDownloader` 知道这是一个全新的任务或一个之前失败的任务，于是开始执行完整的下载、解析和保存流程。

### **第四步：下载后更新记录**

*   每处理完一个 URL（无论成功还是失败），`XDownloader` 都会调用 `record_manager.save_record()` 方法。
*   这个方法会更新内存中的记录，并将最新的状态**原子性地写回**到 `output/records.csv` 文件中，确保下次运行时能够读取到最新的状态。
