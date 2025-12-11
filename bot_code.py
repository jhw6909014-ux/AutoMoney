import os
import time
import random
import logging
import smtplib
import urllib.parse
import feedparser
import google.generativeai as genai
from email.mime.text import MIMEText
from email.header import Header

# --- V29 CONFIG (Blogger Edition) ---
SHOPEE_ID = "16332290023"
BOT_PERSONA = "3C科技發燒友"
KEYWORD_POOL = ["iPhone","Android","顯示卡","AI","筆電","藍芽耳機","Switch","PS5","智慧手錶","行動電源"]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def get_dynamic_rss():
    target_keyword = random.choice(KEYWORD_POOL)
    logger.info(f"🎯 鎖定關鍵字: {target_keyword}")
    encoded = urllib.parse.quote(target_keyword)
    rss_url = f"https://news.google.com/rss/search?q={encoded}+when:1d&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    return rss_url, target_keyword

def create_shopee_button(keyword):
    safe_keyword = urllib.parse.quote(keyword)
    url = f"https://shopee.tw/search?keyword={safe_keyword}&utm_source=affiliate&utm_campaign={SHOPEE_ID}"
    return f"""
    <div style="margin:40px 0;text-align:center;">
        <p style="font-size:15px;color:#666;margin-bottom:10px;">👇 想找 {keyword} 相關優惠？ 👇</p>
        <a href="{url}" target="_blank" rel="nofollow" 
           style="background-color:#ea580c;color:white;padding:15px 30px;border-radius:50px;text-decoration:none;font-weight:bold;font-size:18px;box-shadow:0 4px 10px rgba(234,88,12,0.4);">
           🔍 點此在蝦皮搜尋「{keyword}」
        </a>
    </div>
    """

def send_email_to_blogger(title, html_content):
    sender = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    recipient = os.environ.get("BLOGGER_EMAIL")

    if not sender or not password or not recipient:
        logger.error("❌ 缺少 Email 設定 (GMAIL_USER, GMAIL_APP_PASSWORD, BLOGGER_EMAIL)")
        return False

    msg = MIMEText(html_content, 'html', 'utf-8')
    msg['Subject'] = Header(title, 'utf-8')
    msg['From'] = sender
    msg['To'] = recipient

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        logger.info("✅ Email 發送成功！文章已發布到 Blogger。")
        return True
    except Exception as e:
        logger.error(f"❌ Email 發送失敗: {e}")
        return False

def ai_writer(title, summary, keyword):
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key: return None
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    你是一位【{BOT_PERSONA}】。
    本次主題關鍵字是：【{keyword}】。
    
    請將以下新聞改寫成一篇繁體中文部落格文章。
    新聞標題: {title}
    新聞摘要: {summary}
    
    【寫作指令】:
    1. 標題：必須包含「{keyword}」，並且要是吸引人的農場標題。
    2. 內容：請自然地將 {keyword} 融入文章中。
    3. 表格：請製作一個 HTML 表格 (<table>)，列出關於 {keyword} 的相關規格比較、選購指南或優缺點分析。
    4. 結尾：給出針對 {keyword} 的具體購買建議。
    """
    
    for _ in range(3):
        try:
            res = model.generate_content(prompt)
            if res.text:
                text = res.text.replace("```html", "").replace("```", "")
                btn = create_shopee_button(keyword)
                return text + btn
        except:
            time.sleep(2)
    return None

def main():
    logger.info("V29 Blogger Bot Started...")
    rss_url, target_keyword = get_dynamic_rss()
    feed = feedparser.parse(rss_url)
    
    history = []
    if os.path.exists("history.txt"):
        with open("history.txt", "r") as f: history = f.read().splitlines()
        
    for entry in feed.entries[:1]:
        if entry.link in history: continue
        
        logger.info(f"Processing: {entry.title}")
        content = ai_writer(entry.title, getattr(entry, "summary", ""), target_keyword)
        
        if content:
            # 發送到 Blogger
            success = send_email_to_blogger(f"【{target_keyword}快訊】{entry.title}", content)
            
            if success:
                with open("history.txt", "a") as f: f.write(f"{entry.link}\n")

if __name__ == "__main__":
    main()
