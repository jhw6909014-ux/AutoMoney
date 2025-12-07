import os
import smtplib
import feedparser
import time
import urllib.parse
import google.generativeai as genai
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ================= 1. 設定區 =================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
BLOGGER_EMAIL = os.environ.get("BLOGGER_EMAIL")

SHOPEE_LINKS = {
    "default": "https://s.shopee.tw/8KiFryWcEl",
    "apple": "https://s.shopee.tw/9zqTr3UP7A",
    "iphone": "https://s.shopee.tw/9zqTr3UP7A",
    "samsung": "https://s.shopee.tw/6KxBUKQqDm",
    "android": "https://s.shopee.tw/20oCKNKJh9",
    "pixel": "https://s.shopee.tw/20oCKNKJh9",
    "nvidia": "https://s.shopee.tw/1BF5Kr62JB",
    "laptop": "https://s.shopee.tw/1BF5Kr62JB",
    "game": "https://s.shopee.tw/5AlE6FC4H5",
    "switch": "https://s.shopee.tw/5AlE6FC4H5",
    "ps5": "https://s.shopee.tw/5AlE6FC4H5"
}

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
RSS_URL = "https://www.theverge.com/rss/index.xml"

# ================= 2. 功能區 =================
def get_tech_image(title):
    safe_prompt = urllib.parse.quote(f"{title}, futuristic technology, cinematic lighting, 8k, cyberpunk")
    img_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=600&nologo=true&seed={int(time.time())}&model=flux"
    return f'<div style="text-align:center; margin-bottom:20px;"><img src="{img_url}" style="width:100%; max-width:800px; border-radius:12px;"></div>'

def get_best_link(title, content):
    text = (title + " " + content).lower()
    for k, v in SHOPEE_LINKS.items():
        if k in text and k != "default": return v
    return SHOPEE_LINKS["default"]

def ai_process_article(title, summary, link):
    if not model: return None, None
    
    # 🔥 SEO 優化 Prompt
    prompt = f"""
    任務：將以下科技新聞改寫成「繁體中文」的「3C評測/懶人包」風格文章。
    
    【新聞標題】{title}
    【新聞摘要】{summary}
    
    【SEO 關鍵字策略 (標題必填)】
    1. 標題必須包含：評價、推薦、缺點、PTT熱議、懶人包、規格比較 (擇一使用)。
    2. 標題範例：「{title} 值得買嗎？優缺點分析與價格整理」。

    【內文結構】
    1. **痛點切入**：用「你是否也覺得...」開頭。
    2. **重點分析**：介紹新聞重點。
    3. **中段廣告**：在第二段結束後，插入一句「💡 點此查看最新優惠價格」，並設為超連結({link})。
    4. **優缺點條列**：列出 3 個優點與 1 個缺點。
    5. **結論**：勸敗或建議觀望。

    【回傳 JSON】: {{"category": "科技快訊", "html_body": "HTML內容"}}
    【文末按鈕】: <br><div style="text-align:center;margin:30px;"><a href="{link}" style="background:#007bff;color:white;padding:15px 30px;text-decoration:none;border-radius:50px;font-weight:bold;">🔥 查看 {title} 優惠 (蝦皮)</a></div>
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        import json
        data = json.loads(text[text.find('{'):text.rfind('}')+1])
        return data["category"], data["html_body"]
    except: return None, None

def send_email(subject, category, body):
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = BLOGGER_EMAIL
    msg['Subject'] = f"{subject} #{category}"
    msg.attach(MIMEText(body, 'html'))
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("✅ 發送成功")
    except: pass

if __name__ == "__main__":
    feed = feedparser.parse(RSS_URL)
    if feed.entries:
        entry = feed.entries[0]
        print(f"📄 {entry.title}")
        link = get_best_link(entry.title, getattr(entry, 'summary', ''))
        img = get_tech_image(entry.title)
        cat, html = ai_process_article(entry.title, getattr(entry, 'summary', ''), link)
        if html: send_email(entry.title, cat, img + html)
