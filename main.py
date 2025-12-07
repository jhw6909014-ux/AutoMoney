import os
import smtplib
import feedparser
import time
import urllib.parse
import random # 新增隨機模組
import google.generativeai as genai
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ================= 1. 讀取密碼 =================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
BLOGGER_EMAIL = os.environ.get("BLOGGER_EMAIL")

# ================= 2. 蝦皮連結 =================
SHOPEE_LINKS = {
    "default": "https://s.shopee.tw/8KiFryWcEl",
    "apple": "https://s.shopee.tw/9zqTr3UP7A", "iphone": "https://s.shopee.tw/9zqTr3UP7A",
    "ipad": "https://s.shopee.tw/9zqTr3UP7A", "ios": "https://s.shopee.tw/9zqTr3UP7A",
    "samsung": "https://s.shopee.tw/6KxBUKQqDm", "galaxy": "https://s.shopee.tw/6KxBUKQqDm",
    "android": "https://s.shopee.tw/20oCKNKJh9", "pixel": "https://s.shopee.tw/20oCKNKJh9", "phone": "https://s.shopee.tw/20oCKNKJh9",
    "nvidia": "https://s.shopee.tw/1BF5Kr62JB", "amd": "https://s.shopee.tw/1BF5Kr62JB", "gpu": "https://s.shopee.tw/1BF5Kr62JB", "laptop": "https://s.shopee.tw/1BF5Kr62JB", "computer": "https://s.shopee.tw/1BF5Kr62JB",
    "game": "https://s.shopee.tw/5AlE6FC4H5", "switch": "https://s.shopee.tw/5AlE6FC4H5", "ps5": "https://s.shopee.tw/5AlE6FC4H5"
}

# ================= 3. AI 設定 =================
genai.configure(api_key=GOOGLE_API_KEY)
def get_valid_model():
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini' in m.name: return genai.GenerativeModel(m.name)
        return None
    except: return None

model = get_valid_model()
RSS_URL = "https://www.theverge.com/rss/index.xml"

# ================= 4. 智慧配圖 =================
def get_tech_image(title):
    magic_prompt = f"{title}, futuristic technology, cinematic lighting, unreal engine 5 render, 8k resolution, cyberpunk style"
    safe_prompt = urllib.parse.quote(magic_prompt)
    seed = int(time.time())
    img_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=600&nologo=true&seed={seed}&model=flux"
    return f'<div style="text-align:center; margin-bottom:20px;"><img src="{img_url}" style="width:100%; max-width:800px; border-radius:12px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);"></div>'

def get_best_link(title, content):
    text_to_check = (title + " " + content).lower()
    for keyword, link in SHOPEE_LINKS.items():
        if keyword in text_to_check and keyword != "default": return link
    return SHOPEE_LINKS["default"]

# ================= 6. AI 寫作 (人格分裂版) =================
def ai_process_article(title, summary, shopee_link):
    if not model: return None, None
    
    # === 科技人格轉盤 ===
    styles = [
        "風格：一位毒舌的資深工程師，講話犀利，喜歡吐槽缺點，但最後還是會給出中肯建議。",
        "風格：一位超級興奮的科技迷(Fanboy)，對新功能感到驚艷，語氣充滿熱情，用詞誇張。",
        "風格：一位理性的數據分析師，喜歡列點比較，講究 CP 值，語氣專業冷靜。",
        "風格：一位精打細算的小資族，只在乎這產品值不值得買，會一直強調『省錢』和『優惠』。"
    ]
    selected_style = random.choice(styles)
    print(f"🤖 AI 今日人格：{selected_style}")

    prompt = f"""
    任務：將以下科技新聞改寫成繁體中文部落格文章。
    【標題】{title}
    【摘要】{summary}
    
    【寫作指令】
    1. **請嚴格扮演此角色**：{selected_style}
    2. **SEO標題**：必須包含「評價、推薦、缺點、懶人包」其中之一。
    3. **中段導購**：在第二段結束後，自然插入一句「💡 點此查看最新優惠價格」，並設為超連結({shopee_link})。
    
    【回傳 JSON】：{{"category": "科技快訊", "html_body": "HTML內容"}}
    【文末按鈕】：<br><div style="text-align:center;margin:30px;"><a href="{shopee_link}" style="background:#ee4d2d;color:white;padding:15px 30px;text-decoration:none;border-radius:50px;font-weight:bold;">🔥 點此查看熱門優惠 (蝦皮商城)</a></div>
    """
    try:
        response = model.generate_content(prompt)
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        import json
        start = raw_text.find('{')
        end = raw_text.rfind('}') + 1
        data = json.loads(raw_text[start:end])
        return data.get("category", "科技快訊"), data.get("html_body", "")
    except: return "科技新知", f"<p>{summary}</p><br><div style='text-align:center'><a href='{shopee_link}'>點此查看詳情</a></div>"

# ================= 7. 寄信 =================
def send_email(subject, category, body_html):
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = BLOGGER_EMAIL
    msg['Subject'] = f"{subject} #{category}"
    msg.attach(MIMEText(body_html, 'html'))
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ 發布成功：{category}")
    except: pass

if __name__ == "__main__":
    if not GMAIL_APP_PASSWORD or not model: exit(1)
    feed = feedparser.parse(RSS_URL)
    if feed.entries:
        entry = feed.entries[0]
        my_link = get_best_link(entry.title, getattr(entry, 'summary', ''))
        img_html = get_tech_image(entry.title)
        category, text_html = ai_process_article(entry.title, getattr(entry, 'summary', ''), my_link)
        if text_html: send_email(entry.title, category, img_html + text_html)
    else: print("📭 無新文章")
