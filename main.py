import os
import smtplib
import feedparser
import time
import urllib.parse # 新增這個工具來處理網址
import google.generativeai as genai
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ================= 1. 讀取密碼 =================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
BLOGGER_EMAIL = os.environ.get("BLOGGER_EMAIL")

# ================= 2. 自動偵測可用模型 =================
genai.configure(api_key=GOOGLE_API_KEY)

def get_valid_model():
    try:
        print("🔍 正在偵測您的 API Key 可用的模型...")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini' in m.name:
                    print(f"✅ 找到可用模型：{m.name}")
                    return genai.GenerativeModel(m.name)
        return None
    except:
        return None

model = get_valid_model()
RSS_URL = "https://www.theverge.com/rss/index.xml"

# ================= 3. 強制配圖功能 =================

def get_image_tag(title):
    """
    這是一個強制產生圖片的功能。
    它會把英文標題轉成圖片網址，確保圖片一定會出現。
    """
    # 把標題轉成網址安全格式
    safe_title = urllib.parse.quote(title) 
    img_url = f"https://image.pollinations.ai/prompt/{safe_title}?width=1024&height=512&nologo=true&seed={int(time.time())}"
    
    # 回傳 HTML 圖片語法
    return f'<div style="text-align:center; margin-bottom:20px;"><img src="{img_url}" style="width:100%; max-width:800px; border-radius:12px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"></div>'

def ai_write_body(title, summary, link):
    if not model: return None
    print(f"🤖 AI 正在撰寫內文：{title}...")
    
    prompt = f"""
    請將以下科技新聞改寫成一篇繁體中文部落格文章的「內文」。
    
    【標題】{title}
    【摘要】{summary}
    
    【要求】
    1. 不用給標題（標題我會自己加）。
    2. 不用給圖片（圖片我會自己加）。
    3. 內容要分成三個段落，加入優缺點分析。
    4. 文末加入按鈕：<br><div style="text-align:center;margin:30px;"><a href="{link}" style="background:#d93025;color:white;padding:15px 30px;text-decoration:none;border-radius:5px;">👉 閱讀完整內容</a></div>
    5. 只回傳 HTML 代碼。
    """
    try:
        response = model.generate_content(prompt)
        return response.text.replace("```html", "").replace("```", "").strip()
    except Exception as e:
        print(f"❌ 生成失敗: {e}")
        return None

def send_email(subject, body_html):
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
        print(f"✅ 信件已寄出！")
    except Exception as e:
        print(f"❌ 寄信失敗: {e}")

# ================= 4. 主程式 =================
if __name__ == "__main__":
    print(">>> 系統啟動 (強制配圖版)...")
    
    if not GMAIL_APP_PASSWORD or not model:
        print("❌ 設定錯誤，請檢查 Secret")
        exit(1)

    feed = feedparser.parse(RSS_URL)
    if feed.entries:
        # 為了測試，我們這次抓第 2 篇新聞 (避免跟剛剛重複)
        entry = feed.entries[1] if len(feed.entries) > 1 else feed.entries[0]
        
        print(f"📄 處理新聞：{entry.title}")
        
        # 1. 程式自己產生圖片 (不靠 AI)
        image_html = get_image_tag(entry.title)
        
        # 2. AI 只要寫字就好
        text_html = ai_write_body(entry.title, getattr(entry, 'summary', ''), entry.link)
        
        if text_html:
            # 3. 把圖片黏在最上面
            final_html = image_html + text_html
            send_email(entry.title, final_html)
    else:
        print("📭 無新文章")
