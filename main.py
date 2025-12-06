import os
import smtplib
import feedparser
import urllib.parse
import google.generativeai as genai
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ================= 1. 讀取密碼 =================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
BLOGGER_EMAIL = os.environ.get("BLOGGER_EMAIL")

# ================= 2. 設定 AI =================
genai.configure(api_key=GOOGLE_API_KEY)

def get_valid_model():
    """自動偵測可用模型"""
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

# ================= 3. 抓取真實圖片 (核心修正) =================

def get_real_image(entry):
    """
    優先抓取 RSS 裡的真實新聞圖片。
    如果抓不到，才用 AI 生成一張「科技感」圖片當備用。
    """
    img_url = None
    
    # 方法 A: 檢查 media_content (大部分科技網站用這個)
    if 'media_content' in entry:
        try:
            img_url = entry.media_content[0]['url']
        except:
            pass
            
    # 方法 B: 檢查 links 裡的圖片連結
    if not img_url and 'links' in entry:
        for link in entry.links:
            if 'image' in link.type:
                img_url = link.href
                break
                
    # 方法 C: 檢查 enclosures (有些網站用這個)
    if not img_url and 'enclosures' in entry:
         try:
            img_url = entry.enclosures[0]['url']
         except:
            pass

    # 如果真的抓不到原圖，用 AI 生成，但加上 "tech concept" 避免畫成動物
    if not img_url:
        print("⚠️ 抓不到原圖，使用 AI 生成備用圖")
        safe_title = urllib.parse.quote(entry.title + " futuristic technology concept art") 
        img_url = f"https://image.pollinations.ai/prompt/{safe_title}?width=1024&height=600&nologo=true"
    else:
        print(f"🖼️ 成功抓取原圖：{img_url}")

    return f'<div style="text-align:center; margin-bottom:20px;"><img src="{img_url}" style="width:100%; max-width:800px; border-radius:12px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"></div>'

# ================= 4. 寫作與寄信 =================

def ai_write_body(title, summary, link):
    if not model: return None
    print(f"🤖 AI 正在撰寫：{title}...")
    
    prompt = f"""
    請將以下科技新聞改寫成一篇繁體中文部落格文章的「內文」。
    
    【標題】{title}
    【摘要】{summary}
    
    【要求】
    1. 不用給標題（我已經有了）。
    2. 不用給圖片（我已經有了）。
    3. 內容要分成三個段落，語氣專業且吸引人。
    4. 文末按鈕：<br><div style="text-align:center;margin:30px;"><a href="{link}" style="background:#d93025;color:white;padding:15px 30px;text-decoration:none;border-radius:5px;">👉 閱讀完整報導</a></div>
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
    print(">>> 系統啟動 (抓取原圖版)...")
    
    if not GMAIL_APP_PASSWORD or not model:
        print("❌ 設定錯誤")
        exit(1)

    feed = feedparser.parse(RSS_URL)
    if feed.entries:
        # 測試用：抓第一篇
        entry = feed.entries[0]
        print(f"📄 處理新聞：{entry.title}")
        
        # 1. 抓真正的圖片
        image_html = get_real_image(entry)
        
        # 2. AI 寫文章
        text_html = ai_write_body(entry.title, getattr(entry, 'summary', ''), entry.link)
        
        if text_html:
            # 3. 組合
            final_html = image_html + text_html
            send_email(entry.title, final_html)
    else:
        print("📭 無新文章")
