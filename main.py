import os
import smtplib
import feedparser
import google.generativeai as genai
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ================= 1. 讀取密碼 =================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
BLOGGER_EMAIL = os.environ.get("BLOGGER_EMAIL")

# ================= 2. 自動偵測可用模型 (資深修復) =================
genai.configure(api_key=GOOGLE_API_KEY)

def get_valid_model():
    """直接問 Google 這把鑰匙能用誰，不再瞎猜"""
    try:
        print("🔍 正在偵測您的 API Key 可用的模型...")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini' in m.name:
                    print(f"✅ 找到可用模型：{m.name}")
                    return genai.GenerativeModel(m.name)
        print("❌ 您的 API Key 沒有任何 Gemini 權限，請重新申請！")
        return None
    except Exception as e:
        print(f"❌ API 連線失敗: {e}")
        return None

# 初始化模型 (自動抓取)
model = get_valid_model()
RSS_URL = "https://www.theverge.com/rss/index.xml"

# ================= 3. 寫作與寄信功能 =================

def ai_write_article(title, summary, link):
    if not model: return None
    print(f"🤖 AI 正在撰寫：{title}...")
    
    prompt = f"""
    請將以下科技新聞改寫成一篇繁體中文部落格文章 (HTML 格式)。
    【標題】{title}
    【摘要】{summary}
    【要求】
    1. 標題用 <h2>。
    2. 插入圖片：<br><div style="text-align:center;"><img src="https://image.pollinations.ai/prompt/{title.replace(' ', '%20')}?nologo=true" style="width:100%;max-width:600px;border-radius:10px;"></div><br>
    3. 文末按鈕：<br><div style="text-align:center;margin:30px;"><a href="{link}" style="background:#d93025;color:white;padding:15px 30px;text-decoration:none;border-radius:5px;">👉 閱讀完整內容</a></div>
    4. 只給 HTML。
    """
    try:
        response = model.generate_content(prompt)
        return response.text.replace("```html", "").replace("```", "").strip()
    except Exception as e:
        print(f"❌ 生成失敗: {e}")
        return None

def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = BLOGGER_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ 信件已寄出！")
    except Exception as e:
        print(f"❌ 寄信失敗: {e}")

# ================= 4. 主程式 =================
if __name__ == "__main__":
    print(">>> 系統啟動 (自動偵測版)...")
    
    if not GMAIL_APP_PASSWORD:
        print("❌ 錯誤：找不到密碼")
        exit(1)
        
    if not model:
        print("❌ 致命錯誤：AI 模型初始化失敗，請檢查 API Key。")
        exit(1)

    feed = feedparser.parse(RSS_URL)
    if feed.entries:
        entry = feed.entries[0]
        html = ai_write_article(entry.title, getattr(entry, 'summary', ''), entry.link)
        if html:
            send_email(entry.title, html)
    else:
        print("📭 無新文章")
