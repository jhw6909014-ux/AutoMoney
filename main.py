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
                if 'gemini' in m.name:
                    return genai.GenerativeModel(m.name)
        return None
    except:
        return None

model = get_valid_model()
# 科技版原本的 RSS 其實還可以，但為了確保穩定，這裡建議也可以換成 Google News
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
    for keyword, link in SHOPEE_LINKS.items():
        if keyword in text_to_check and keyword != "default":
            print(f"💰 偵測到商機關鍵字：[{keyword}]")
            return link
    return SHOPEE_LINKS["default"]

# ================= 6. AI 寫作 (SEO 優化版) =================
def ai_process_article(title, summary, shopee_link):
    if not model: return None, None
    print(f"🤖 AI 正在撰寫：{title}...")
    
    # 🔥 SEO 優化 Prompt
    prompt = f"""
    任務：將以下科技新聞改寫成「繁體中文」的「3C評測/懶人包」部落格文章。
    
    【標題】{title}
    【摘要】{summary}
    
    【SEO 關鍵字策略 (標題必填)】
    1. 標題必須包含：評價、推薦、缺點、PTT熱議、懶人包、規格比較 (擇一使用)。
    2. 標題範例：「{title} 值得買嗎？優缺點分析與價格整理」。

    【內文結構要求】
    1. **痛點切入**：用「你是否也覺得...」或「大家期待已久的...」開頭。
    2. **重點分析**：介紹新聞重點與規格。
    3. **中段廣告 (重要)**：在第二段結束後，自然插入一句「💡 點此查看最新優惠價格」，並設為超連結({shopee_link})。
    4. **優缺點條列**：列出 3 個優點與 1 個缺點。
    5. **結論**：勸敗或建議觀望。
    
    【回傳格式 (JSON)】：
    {{
        "category": "科技快訊",
        "html_body": "這裡填 HTML 內容"
    }}
    
    【文末按鈕】：
    <br><div style="text-align:center;margin:30px;"><a href="{shopee_link}" style="background:#ee4d2d;color:white;padding:15px 30px;text-decoration:none;border-radius:50px;font-weight:bold;box-shadow: 0 4px 6px rgba(0,0,0,0.1);">🔥 點此查看熱門優惠 (蝦皮商城)</a></div>
    """
    
    try:
        response = model.generate_content(prompt)
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        import json
        start = raw_text.find('{')
        end = raw_text.rfind('}') + 1
        data = json.loads(raw_text[start:end])
        return data.get("category", "科技快訊"), data.get("html_body", "")
    except Exception as e:
        print(f"❌ AI 處理失敗: {e}")
        return "科技新知", f"<p>{summary}</p><br><div style='text-align:center'><a href='{shopee_link}'>點此查看詳情</a></div>"

# ================= 7. 寄信 =================
def send_email(subject, category, body_html):
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = BLOGGER_EMAIL
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
    print(">>> 系統啟動 (科技版)...")
    if not GMAIL_APP_PASSWORD or not model: exit(1)
    feed = feedparser.parse(RSS_URL)
    if feed.entries:
        entry = feed.entries[0]
        print(f"📄 處理新聞：{entry.title}")
        my_link = get_best_link(entry.title, getattr(entry, 'summary', ''))
        img_html = get_tech_image(entry.title)
        category, text_html = ai_process_article(entry.title, getattr(entry, 'summary', ''), my_link)
        if text_html:
            send_email(entry.title, category, img_html + text_html)
    else:
        print("📭 無新文章")
