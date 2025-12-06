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

# ================= 2. 【賺錢核心】蝦皮分潤連結區 =================
# 這是你剛剛產生的 8 個賺錢連結，我已經幫你對應好了
SHOPEE_LINKS = {
    # 1. 預設 (蝦皮首頁) - 當沒對到關鍵字時用這個
    "default": "https://s.shopee.tw/8KiFryWcEl",
    
    # 2. 手機與蘋果區 (對應 iPhone 連結)
    "apple": "https://s.shopee.tw/9zqTr3UP7A",
    "iphone": "https://s.shopee.tw/9zqTr3UP7A",
    "ipad": "https://s.shopee.tw/9zqTr3UP7A",
    "ios": "https://s.shopee.tw/9zqTr3UP7A",
    
    # 3. 三星區 (對應 Samsung 連結)
    "samsung": "https://s.shopee.tw/6KxBUKQqDm",
    "galaxy": "https://s.shopee.tw/6KxBUKQqDm",
    
    # 4. 安卓通用區 (對應 Android 連結)
    "android": "https://s.shopee.tw/20oCKNKJh9",
    "pixel": "https://s.shopee.tw/20oCKNKJh9",
    "phone": "https://s.shopee.tw/20oCKNKJh9",
    
    # 5. 電腦與顯卡區 (對應 顯卡 連結)
    "nvidia": "https://s.shopee.tw/1BF5Kr62JB",
    "amd": "https://s.shopee.tw/1BF5Kr62JB",
    "gpu": "https://s.shopee.tw/1BF5Kr62JB",
    "laptop": "https://s.shopee.tw/1BF5Kr62JB",
    "computer": "https://s.shopee.tw/1BF5Kr62JB",
    
    # 6. 生活用品區 (對應 衛生紙 連結)
    "tissue": "https://s.shopee.tw/20oCKOgK9C",
    "life": "https://s.shopee.tw/20oCKOgK9C",
    "home": "https://s.shopee.tw/20oCKOgK9C",
    
    # 7. 美食零食區 (對應 零食 連結)
    "food": "https://s.shopee.tw/9UuDGBvyXc",
    "snack": "https://s.shopee.tw/9UuDGBvyXc",
    "eat": "https://s.shopee.tw/9UuDGBvyXc",
    
    # 8. 遊戲與娛樂區 (對應 遊戲 連結)
    "game": "https://s.shopee.tw/5AlE6FC4H5",
    "switch": "https://s.shopee.tw/5AlE6FC4H5",
    "ps5": "https://s.shopee.tw/5AlE6FC4H5",
    "steam": "https://s.shopee.tw/5AlE6FC4H5",
    "sony": "https://s.shopee.tw/5AlE6FC4H5"
}

# ================= 3. AI 設定 =================
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

# ================= 4. 智慧配圖 =================
def get_tech_image(title):
    magic_prompt = f"{title}, futuristic technology, cinematic lighting, unreal engine 5 render, 8k resolution, cyberpunk style"
    safe_prompt = urllib.parse.quote(magic_prompt)
    seed = int(time.time())
    img_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=600&nologo=true&seed={seed}&model=flux"
    return f'<div style="text-align:center; margin-bottom:20px;"><img src="{img_url}" style="width:100%; max-width:800px; border-radius:12px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);"></div>'

# ================= 5. 智慧選連結 =================
def get_best_link(title, content):
    text_to_check = (title + " " + content).lower()
    
    # 優先對比關鍵字
    for keyword, link in SHOPEE_LINKS.items():
        if keyword in text_to_check and keyword != "default":
            print(f"💰 偵測到商機關鍵字：[{keyword}] -> 插入專屬連結")
            return link
            
    print("💰 使用預設首頁連結")
    return SHOPEE_LINKS["default"]

# ================= 6. AI 寫作 =================
def ai_process_article(title, summary, shopee_link):
    if not model: return None, None
    print(f"🤖 AI 正在撰寫：{title}...")
    
    prompt = f"""
    任務：將以下科技新聞改寫成繁體中文部落格文章。
    
    【標題】{title}
    【摘要】{summary}
    
    【要求】
    1. **分類標籤**：請判斷這篇文章屬於哪個類別（例如：Apple專區、安卓手機、遊戲快訊、AI科技、生活新知）。
    2. **內文撰寫**：分成三段，語氣專業且幽默，吸引人閱讀。
    3. **推銷植入**：在文章最後，加上一個按鈕。
    
    【回傳格式 (JSON)】：
    請直接回傳一個 JSON 格式，包含兩個欄位：
    {{
        "category": "這裡填分類名稱",
        "html_body": "這裡填文章的 HTML 內容"
    }}
    
    【HTML 內文按鈕格式】：
    <br><div style="text-align:center;margin:30px;"><a href="{shopee_link}" style="background:#ee4d2d;color:white;padding:15px 30px;text-decoration:none;border-radius:50px;font-weight:bold;box-shadow: 0 4px 6px rgba(0,0,0,0.1);">🔥 點此查看熱門優惠 (蝦皮商城)</a></div>
    """
    
    try:
        response = model.generate_content(prompt)
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        
        import json
        start = raw_text.find('{')
        end = raw_text.rfind('}') + 1
        json_str = raw_text[start:end]
        
        data = json.loads(json_str)
        return data.get("category", "科技快訊"), data.get("html_body", "")
        
    except Exception as e:
        print(f"❌ AI 處理失敗: {e}")
        return "科技新知", f"<p>{summary}</p><br><div style='text-align:center'><a href='{shopee_link}'>點此查看詳情</a></div>"

# ================= 7. 寄信 =================
def send_email(subject, category, body_html):
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = BLOGGER_EMAIL
    
    # 標題加入 #標籤，Blogger 會自動分類
    final_subject = f"{subject} #{category}"
    
    msg['Subject'] = final_subject
    msg.attach(MIMEText(body_html, 'html'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ 信件已寄出！分類標籤：{category}")
    except Exception as e:
        print(f"❌ 寄信失敗: {e}")

# ================= 8. 主程式 =================
if __name__ == "__main__":
    print(">>> 系統啟動 (蝦皮分潤完全體)...")
    
    if not GMAIL_APP_PASSWORD or not model:
        exit(1)

    feed = feedparser.parse(RSS_URL)
    if feed.entries:
        # 測試用：抓最新的
        entry = feed.entries[0]
        print(f"📄 處理新聞：{entry.title}")
        
        # 1. 決定連結 (掃描標題有沒有 遊戲、蘋果、安卓 等字眼)
        my_link = get_best_link(entry.title, getattr(entry, 'summary', ''))
        
        # 2. 產生圖片
        img_html = get_tech_image(entry.title)
        
        # 3. AI 寫文
        category, text_html = ai_process_article(entry.title, getattr(entry, 'summary', ''), my_link)
        
        if text_html:
            final_html = img_html + text_html
            send_email(entry.title, category, final_html)
    else:
        print("📭 無新文章")
