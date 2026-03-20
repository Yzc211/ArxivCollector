---

# arXiv Paper Collector（简易版）

脚本功能：自动从 arXiv 抓取指定关键词的最新、不重复的论文，下载 PDF 至本地文件夹、收集论文相关信息（title、author、published date、URL等）到 Excel，并发送更新通知到指定邮件。

支持将大小写不同但语义相同的关键词归到同一个文件夹，并可对 PDF 下载失败提示。

---

## 功能特点

* 指定关键词抓取最新论文（支持标题和摘要匹配，大小写忽略）
* 自动下载 PDF 文件
* 保存历史 Excel（避免重复抓取）
* 解析摘要中的 GitHub/GitLab/HuggingFace 链接
* 自动发送邮件通知（正文 + Excel 附件）
* 可通过定时任务实现定期抓取（Windows/Linux）

---

## 安装依赖

建议使用 Python 3.10+，并创建虚拟环境：

```bash
# 创建虚拟环境
python -m venv venv
# 激活环境
# Windows
venv\Scripts\activate
# Linux / Mac
source venv/bin/activate
```

安装依赖：

```bash
pip install -r requirements.txt
```
---

## 配置说明

编辑 `papercollect.py` 文件中的配置部分：

```python
# ---------------- 配置 ----------------
KEYWORDS = [
    "referring multi-object tracking",
    "Referring Multi-Object Tracking",
    "RMOT",
    "visual-language tracking",
    "Visual-Language Tracking"
]
MAX_RESULTS = 30           # 每个关键词抓取数量
DAYS_BACK = 20             # 最近多少天的论文
SAVE_FOLDER = "arxiv_papers"
EXCEL_FILE = "arxiv_papers.xlsx"
CATEGORIES = ['cs.CV','cs.LG']
CHUNK_SIZE = 1024*1024
TIMEOUT = 60
SLEEP_BETWEEN_REQUESTS = 3
ARXIV_RETRY_DELAY = 10     # 请求限制等待秒数

KEYWORD_FOLDERS = {        # 关键词映射到文件夹
    "referring multi-object tracking": "Referring_Multi_Object_Tracking",
    "Referring Multi-Object Tracking": "Referring_Multi_Object_Tracking",
    "RMOT": "Referring_Multi_Object_Tracking",
    "visual-language tracking": "Visual_Language_Tracking",
    "Visual-Language Tracking": "Visual_Language_Tracking"
}

# ---------------- 邮件配置 ----------------
EMAIL_CONFIG = {
    "smtp_server": "smtp.163.com",
    "smtp_port": 465,
    "sender_email": "你的邮箱@163.com",
    "sender_password": "你的授权码",
    "receiver_email": "接收邮箱@example.com"
}
```

**注意**：

* `sender_password` 为 SMTP 邮箱授权码（非登录密码），可在 163 邮箱设置 → POP3/SMTP 开启并获取授权码。

---

## 使用方法
直接在IDE中运行python文件或在虚拟环境中运行：

```bash
python papercollect.py
```

脚本会自动：

1. 根据关键词抓取最新论文（标题或摘要匹配）。
2. 下载 PDF 到对应文件夹。
3. 保存历史总 Excel（去重）。
4. 保存当天抓取的新论文 Excel。
5. 通过邮件发送更新（正文 + Excel 附件）。

---

## 定时任务设置

### Windows（任务计划程序）

1. 打开“任务计划程序” → “创建基本任务”
2. 设置名称，如 `arXivPaperUpdate`
3. 触发器选择“每天” → 高级设置“每 3 天重复一次”
4. 操作选择“启动程序”
   * 程序/脚本：Python 可执行路径，例如 `C:\Users\username\miniconda3\python.exe`
   * 参数：脚本路径，例如 `"D:\arxivpaper\ArxivCollector.py"`
5. 高级设置选择“以最高权限运行”，完成任务创建

### Linux / Mac（cron）

1. 打开终端，输入 `crontab -e`
2. 添加定时任务，每 3 天早上 9 点执行：

```cron
0 9 */3 * * /usr/bin/python3 /home/user/arxivpaper/papercollect.py
```

3. 保存并退出，cron 会自动执行。

---

## 邮件通知

* 邮件正文包含论文标题、作者、发布日期、链接、摘要（前 500 字）。
* Excel 附件包含详细信息。
* 若没有抓取到新论文，邮件正文提示“本次没有抓取到新的文献”。

---


## 注意事项

1. arXiv API 有请求限制（429 Too Many Requests），脚本内已内置重试和延时。
2. 下载 PDF 失败不会中断程序，只会提示错误并继续。
3. 邮件发送需要正确配置 SMTP 邮箱和授权码。
4. 建议使用虚拟环境隔离依赖。
