import os
import smtplib
import feedparser
import google.generativeai as genai
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ================= 1. 讀取密碼 (從 GitHub Secrets) =================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
BLOGGER_EMAIL = os.environ.get("BLOGGER_EMAIL")

# ================= 2. 設定 AI 與新聞來源 =================
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# 這裡設定你要抓的新聞來源 (預設是 The Verge 科技新聞)
RSS_URL = "https://www.theverge.com/rss/index.xml"

# 【賺錢連結區】未來你可以把這裡的網址改成你的 Amazon 或 蝦皮推薦連結
AFFILIATE_LINKS = {
    "default": "https://www.google.com" # 預設連結，之後可以改成你的首頁
}

# ================= 3. 核心功能函式 =================

def ai_write_article(title, summary, link):
    """請 AI 寫一篇圖文並茂的文章"""
    print(f"🤖 AI 正在改寫文章：{title}...")
    
    # 這是給 AI 的指令
    prompt = f"""
    請將以下科技新聞改寫成一篇「繁體中文」的部落格文章，格式為 HTML。
    
    【標題】{title}
    【摘要】{summary}
    
    【要求】
    1. 標題要用 <h2> 標籤，寫得非常吸睛（Clickbait 風格）。
    2. 在第一段文字結束後，插入這張封面圖片：
       <br><img src="https://image.pollinations.ai/prompt/{title.replace(' ', '%20')}?nologo=true" style="width:100%;border-radius:10px;margin:20px 0;"><br>
    3. 內容要分段，包含「重點分析」和「優缺點比較」。
    4. 文章最後必須加入這個按鈕：
       <div style="text-align:center;margin-top:30px;">
           <a href="{link}" style="background-color:#d93025;color:white;padding:15px 30px;text-decoration:none;border-radius:5px;font-weight:bold;font-size:18px;">👉 點此查看詳細內容</a>
       </div>
    5. 直接給我 HTML 程式碼，不要包含 ```html 這種標記。
    """
    
    try:
        response = model.generate_content(prompt)
        # 清理 AI 有時候會多給的符號
        return response.text.replace("```html", "").replace("```", "").strip()
    except Exception as e:
        print(f"❌ AI 生成失敗: {e}")
        return None

def send_email_to_blogger(subject, body_html):
    """寄信給 Blogger 發布文章"""
    print("📧 正在寄信給 Blogger...")
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = BLOGGER_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body_html, 'html'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ 成功發布文章！標題：{subject}")
    except Exception as e:
        print(f"❌ 發信錯誤: {e}")

# ================= 4. 主程式啟動點 =================
if __name__ == "__main__":
    print(">>> 系統啟動中...")
    
    # 檢查密碼是否存在
    if not GMAIL_APP_PASSWORD or not GOOGLE_API_KEY:
        print("❌ 錯誤：找不到密碼，請檢查 GitHub Secrets 設定！")
        exit(1)
        
    # 抓取新聞
    feed = feedparser.parse(RSS_URL)
    print(f"📡 抓取 RSS 成功，來源：{feed.feed.title}")

    # 為了避免洗版，每次執行只抓「最新的一篇」
    if len(feed.entries) > 0:
        entry = feed.entries[0]
        html_content = ai_write_article(entry.title, getattr(entry, 'summary', ''), entry.link)
        
        if html_content:
            send_email_to_blogger(entry.title, html_content)
    else:
        print("📭 目前沒有新文章。")
