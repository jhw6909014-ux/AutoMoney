import os
import smtplib
import feedparser
import time
import urllib.parse
import google.generativeai as genai
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ================= 1. 讀取密碼 =================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
BLOGGER_EMAIL = os.environ.get("BLOGGER_EMAIL")

# ================= 2. 設定 AI (自動偵測) =================
genai.configure(api_key=GOOGLE_API_KEY)

def get_valid_model():
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini' in m.name:
                    return genai.GenerativeModel(m.name)
        return None
    except:
        return None

model = get_valid_model()
RSS_URL = "https://www.theverge.com/rss/index.xml"

# ================= 3. 高質感圖片生成 (關鍵修改) =================

def get_tech_image(title):
    """
    不抓醜圖了，直接用 AI 生成「高科技風格」的桌布級圖片。
    加上 keywords 讓圖片變成 3D 渲染風格，避免奇怪的拼貼。
    """
    # 這裡我們加上「魔法咒語」，強迫 AI 畫出好看的圖
    magic_prompt = f"{title}, futuristic technology, cinematic lighting, unreal engine 5 render, 8k resolution, hyperrealistic, cyberpunk style"
    
    # 轉成網址格式
    safe_prompt = urllib.parse.quote(magic_prompt)
    
    # 加入隨機數 seed，確保每次圖片都不一樣
    seed = int(time.time())
    
    img_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=600&nologo=true&seed={seed}&model=flux"
    
    return f'<div style="text-align:center; margin-bottom:20px;"><img src="{img_url}" style="width:100%; max-width:800px; border-radius:12px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);"></div>'

# ================= 4. 寫作與寄信 =================

def ai_write_body(title, summary, link):
    if not model: return None
    print(f"🤖 AI 正在撰寫：{title}...")
    
    prompt = f"""
    請將以下科技新聞改寫成一篇繁體中文部落格文章的「內文」。
    
    【標題】{title}
    【摘要】{summary}
    
    【要求】
    1. 不用給標題（我會自己加）。
    2. 不用給圖片（我會自己加）。
    3. 內容要分成三個段落，語氣要像「科技媒體總編輯」那樣專業。
    4. 文末按鈕：<br><div style="text-align:center;margin:30px;"><a href="{link}" style="background:#d93025;color:white;padding:15px 30px;text-decoration:none;border-radius:5px;font-weight:bold;">👉 閱讀完整報導</a></div>
    5. 只回傳 HTML。
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

# ================= 5. 主程式 =================
if __name__ == "__main__":
    print(">>> 系統啟動 (高質感濾鏡版)...")
    
    if not GMAIL_APP_PASSWORD or not model:
        print("❌ 設定錯誤")
        exit(1)

    feed = feedparser.parse(RSS_URL)
    if feed.entries:
        # 為了測試，我們換一篇抓 (抓第3篇，避免重複)
        # 實際上線會自動抓最新的
        entry = feed.entries[2] if len(feed.entries) > 2 else feed.entries[0]
        
        print(f"📄 處理新聞：{entry.title}")
        
        # 1. 生成高質感圖片
        image_html = get_tech_image(entry.title)
        
        # 2. AI 寫文章
        text_html = ai_write_body(entry.title, getattr(entry, 'summary', ''), entry.link)
        
        if text_html:
            final_html = image_html + text_html
            send_email(entry.title, final_html)
    else:
        print("📭 無新文章")
