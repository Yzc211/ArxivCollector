import arxiv
import pandas as pd
import os
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# ---------------- 配置 ----------------
KEYWORDS = [
    "referring multi-object tracking",
    "Referring Multi-Object Tracking",
    "RMOT",
    "visual-language tracking",
    "Visual-Language Tracking"
]
MAX_RESULTS = 30
DAYS_BACK = 20
SAVE_FOLDER = "arxiv_papers"
EXCEL_FILE = "arxiv_papers.xlsx"
CATEGORIES = ['cs.CV','cs.LG']
CHUNK_SIZE = 1024*1024
TIMEOUT = 60
SLEEP_BETWEEN_REQUESTS = 3
ARXIV_RETRY_DELAY = 10

# 将大小写不同但语义相同的关键词统一到一个文件夹
KEYWORD_FOLDERS = {
    "referring multi-object tracking": "Referring_Multi_Object_Tracking",
    "Referring Multi-Object Tracking": "Referring_Multi_Object_Tracking",
    "RMOT": "Referring_Multi_Object_Tracking",
    "visual-language tracking": "Visual_Language_Tracking",
    "Visual-Language Tracking": "Visual_Language_Tracking"
}

# --------------- 邮件配置 ----------------
EMAIL_CONFIG = {
    "smtp_server": "smtp.163.com",
    "smtp_port": 465,
    "sender_email": "你的邮箱@163.com",
    "sender_password": "你的授权码",
    "receiver_email": "接收邮箱@example.com"
}
# ---------------------------------------

if not os.path.exists(SAVE_FOLDER):
    os.makedirs(SAVE_FOLDER)

date_from = datetime.now() - timedelta(days=DAYS_BACK)

# 读取已有 Excel
if os.path.exists(EXCEL_FILE):
    df_existing = pd.read_excel(EXCEL_FILE)
    existing_ids = set(df_existing["arXiv ID"].tolist()) if "arXiv ID" in df_existing.columns else set()
else:
    df_existing = pd.DataFrame()
    existing_ids = set()

papers_data = []

def extract_github_link(summary_text):
    soup = BeautifulSoup(summary_text, "html.parser")
    text = soup.get_text()
    for keyword in ["github.com", "gitlab.com", "huggingface.co"]:
        if keyword in text.lower():
            start = text.lower().find(keyword)
            end = text.find(" ", start)
            if end == -1:
                end = len(text)
            return text[start:end]
    return None

def download_pdf(url, filename):
    try:
        r = requests.get(url, stream=True, timeout=TIMEOUT)
        r.raise_for_status()
        with open(filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"下载失败: {filename}, 错误: {e}")
        return False

def send_email(subject, body, attachments=None):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_CONFIG['sender_email']
    msg['To'] = EMAIL_CONFIG['receiver_email']
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    if attachments:
        for filepath in attachments:
            with open(filepath, 'rb') as f:
                part = MIMEApplication(f.read())
                part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(filepath))
                msg.attach(part)
    try:
        server = smtplib.SMTP_SSL(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
        server.send_message(msg)
        server.quit()
        print("邮件发送成功")
    except Exception as e:
        print(f"邮件发送失败: {e}")

# 创建 arXiv client
client = arxiv.Client(page_size=MAX_RESULTS, delay_seconds=SLEEP_BETWEEN_REQUESTS)

for kw in KEYWORDS:
    folder_name = KEYWORD_FOLDERS[kw]
    keyword_folder = os.path.join(SAVE_FOLDER, folder_name)
    if not os.path.exists(keyword_folder):
        os.makedirs(keyword_folder)

    query = f'("{kw}") AND (cat:cs.CV OR cat:cs.LG)'
    search = arxiv.Search(
        query=query,
        max_results=MAX_RESULTS,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )

    # 处理 arXiv 请求及 429
    for attempt in range(5):
        try:
            results = client.results(search)
            break
        except arxiv.HTTPError as e:
            if e.status_code == 429:
                print(f"arXiv 返回 429，等待 {ARXIV_RETRY_DELAY}s 重试 {attempt+1}/5...")
                time.sleep(ARXIV_RETRY_DELAY)
            else:
                print(f"arXiv 请求失败 {attempt+1}/5，错误: {e}")
                time.sleep(ARXIV_RETRY_DELAY)
    else:
        print(f"关键词 {kw} 多次请求失败，跳过")
        continue

    for result in results:
        published = result.published.replace(tzinfo=None)
        if published < date_from:
            continue
        arxiv_id = result.entry_id.split('/')[-1]
        if arxiv_id in existing_ids:
            continue

        title = result.title
        authors = ", ".join([a.name for a in result.authors])
        summary = result.summary.replace('\n', ' ').strip()
        pdf_url = result.pdf_url
        github_link = extract_github_link(summary) or ""

        if not any(k.lower() in (title + " " + summary).lower() for k in KEYWORDS):
            continue

        safe_title = "".join(c if c.isalnum() or c in "_- " else "_" for c in title[:50])
        github_flag = "_GITHUB" if github_link else ""
        pdf_filename = os.path.join(keyword_folder, f"{safe_title}{github_flag}.pdf")

        download_pdf(pdf_url, pdf_filename)  # 下载失败不影响继续

        papers_data.append({
            "Title": title,
            "Authors": authors,
            "Published": published.strftime("%Y-%m-%d"),
            "Summary": summary,
            "arXiv URL": result.entry_id,
            "arXiv ID": arxiv_id,
            "PDF Path": pdf_filename,
            "GitHub Link": github_link,
            "Keyword": kw
        })
        existing_ids.add(arxiv_id)

    time.sleep(SLEEP_BETWEEN_REQUESTS)

# 保存历史 Excel
if df_existing.empty:
    df_total = pd.DataFrame(papers_data)
else:
    df_new = pd.DataFrame(papers_data)
    df_total = pd.concat([df_existing, df_new], ignore_index=True)
    df_total.drop_duplicates(subset=["arXiv ID"], inplace=True)

df_total.to_excel(EXCEL_FILE, index=False)
print(f"历史总论文记录已保存到 {EXCEL_FILE}")

# 保存当天新论文
today_str = datetime.now().strftime("%Y-%m-%d")
new_excel_file = os.path.join(SAVE_FOLDER, f"{today_str}_new_papers.xlsx")
pd.DataFrame(papers_data).to_excel(new_excel_file, index=False)

# 准备邮件正文
if papers_data:
    body = "以下是最新抓取的论文列表:\n\n"
    for p in papers_data:
        body += f"标题: {p['Title']}\n作者: {p['Authors']}\n发表日期: {p['Published']}\n链接: {p['arXiv URL']}\n摘要: {p['Summary'][:500]}...\n\n"
else:
    body = "本次没有抓取到新的文献。"

send_email(f"arXiv 新论文更新 - {today_str}", body, attachments=[new_excel_file])