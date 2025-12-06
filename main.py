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

# ================= 2. 設定 AI (使用標準版 Flash) =================
genai.configure(api_key=GOOGLE_API_KEY)
# 這裡使用最穩定的模型名稱
model = genai.GenerativeModel("gemini-1.5-flash")

RSS_URL = "https://www.theverge.com/rss/index.xml"

# ================= 3. 功能區 =================

def ai_write_article(title, summary, link):
    print(f"🤖 AI 正在撰寫文章：{title}...")
    prompt = f"""
    請將以下科技新聞改寫成一篇繁體中文部落格文章 (HTML 格式)。
    
    【標題】{title}
    【摘要】{summary}
    
    【要求】
    1. 標題使用 <h2> 標籤，要吸引人。
    2. 在第一段結束後，插入這張封面圖：
       <br><div style="text-align:center;"><img src="https://image.pollinations.ai/prompt/{title.replace(' ', '%20')}?nologo=true" style="width:100%; max-width:600px; border-radius:10px;"></div><br>
    3. 內容要有條理，加入優缺點分析。
    4. 文末加入按鈕：
       <br><div style="text-align:center; margin:30px 0;"><a href="{link}" style="background-color:#d93025; color:white; padding:15px 30px; text-decoration:none; border-radius:5px; font-weight:bold;">👉 點此閱讀完整報導</a></div>
    5. 只回傳 HTML 代碼，不要 Markdown 標記。
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.replace("```html", "").replace("```", "").strip()
        return text
    except Exception as e:
        print(f"❌ AI 生成錯誤: {e}")
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
        print(f"✅ 文章已發送至 Blogger：{subject}")
    except Exception as e:
        print(f"❌ 寄信失敗 (請檢查 Gmail 密碼): {e}")

# ================= 4. 主程式 =================
if __name__ == "__main__":
    print(">>> 系統啟動 (v2.0 修正版)...")
    
    if not GMAIL_APP_PASSWORD:
        print("❌ 錯誤：找不到環境變數")
        exit(1)

    try:
        feed = feedparser.parse(RSS_URL)
        if feed.entries:
            # 為了測試穩定性，我們只抓最新的一篇
            entry = feed.entries[0]
            print(f"📄 發現新聞：{entry.title}")
            
            html_content = ai_write_article(entry.title, getattr(entry, 'summary', ''), entry.link)
            
            if html_content:
                send_email(entry.title, html_content)
            else:
                print("⚠️ AI 沒有回傳內容")
        else:
            print("📭 RSS 來源沒有新文章")
            
    except Exception as e:
        print(f"❌ 系統執行錯誤: {e}")
