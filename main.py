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

# ================= 2. 設定 AI =================
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

# ================= 3. AI 導演生圖功能 (最核心的優化) =================

def get_smart_image(title):
    """
    不使用固定關鍵字。
    改為請 AI 根據標題，想像一個具體的畫面，再生成圖片。
    這樣圖片就會跟文章內容 100% 貼合。
    """
    if not model: return ""
    
    print(f"🎨 AI 正在構思圖片畫面：{title}...")
    
    # 1. 請 AI 寫出圖片的英文描述 (Prompt)
    prompt_for_ai = f"""
    You are an AI Art Director. 
    Create a highly detailed, photorealistic image prompt for the following news title: "{title}".
    
    Requirements:
    1. Describe the main subject clearly (e.g., if it's a phone, describe the phone; if it's a movie company, describe a movie set or cinema).
    2. Add style keywords: "Cinematic lighting, 8k resolution, photorealistic, depth of field".
    3. Keep it under 30 words.
    4. ONLY output the prompt text in English. No other words.
    """
    
    try:
        # 取得 AI 建議的畫圖指令
        image_prompt = model.generate_content(prompt_for_ai).text.strip()
        print(f"🖌️ AI 決定畫：{image_prompt}")
        
        # 轉成網址格式
        safe_prompt = urllib.parse.quote(image_prompt)
        seed = int(time.time())
        
        # 使用 Pollinations 生成 (加上 flux 模型讓畫質更好)
        img_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=600&nologo=true&seed={seed}&model=flux"
        
        return f'<div style="text-align:center; margin-bottom:20px;"><img src="{img_url}" style="width:100%; max-width:800px; border-radius:12px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);"></div>'
    
    except Exception as e:
        print(f"⚠️ 生圖失敗，使用備案: {e}")
        # 如果失敗，回退到原本的簡單模式
        safe_title = urllib.parse.quote(title + " technology")
        img_url = f"https://image.pollinations.ai/prompt/{safe_title}?width=1024&height=600&nologo=true"
        return f'<div style="text-align:center; margin-bottom:20px;"><img src="{img_url}" style="width:100%; max-width:800px; border-radius:12px;"></div>'

# ================= 4. 寫作與寄信 =================

def ai_write_body(title, summary, link):
    if not model: return None
    print(f"🤖 AI 正在撰寫內文：{title}...")
    
    prompt = f"""
    請將以下科技新聞改寫成一篇繁體中文部落格文章的「內文」。
    
    【標題】{title}
    【摘要】{summary}
    
    【要求】
    1. 標題與圖片我都有了，你只要寫內文。
    2. 內容分成三段，專業且流暢。
    3. 文末按鈕：<br><div style="text-align:center;margin:30px;"><a href="{link}" style="background:#d93025;color:white;padding:15px 30px;text-decoration:none;border-radius:5px;font-weight:bold;">👉 閱讀完整報導</a></div>
    4. 只回傳 HTML。
    """
    try:
        response = model.generate_content(prompt)
        return response.text.replace("```html", "").replace("```", "").strip()
    except:
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
    print(">>> 系統啟動 (AI 導演版)...")
    
    if not GMAIL_APP_PASSWORD or not model:
        exit(1)

    feed = feedparser.parse(RSS_URL)
    if feed.entries:
        # 為了測試，我們換一篇抓 (避免重複)
        # 上線時它會自動抓最新的
        entry = feed.entries[3] if len(feed.entries) > 3 else feed.entries[0]
        
        print(f"📄 處理新聞：{entry.title}")
        
        # 1. 讓 AI 決定畫什麼 (Smart Image)
        image_html = get_smart_image(entry.title)
        
        # 2. 寫文章
        text_html = ai_write_body(entry.title, getattr(entry, 'summary', ''), entry.link)
        
        if text_html:
            final_html = image_html + text_html
            send_email(entry.title, final_html)
    else:
        print("📭 無新文章")
