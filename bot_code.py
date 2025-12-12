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

# --- CONFIG ---
# 為了避免變數抓不到，我們加強檢查
SHOPEE_ID = "16332290023"
BOT_PERSONA = "專業3C科技發燒友"
KEYWORD_POOL = ["筆電", "顯示卡", "iPhone", "AI PC"]

# 設定 Log，讓它顯示更詳細
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
    return f"""<br><a href="{url}">👉 點此在蝦皮搜尋「{keyword}」</a><br>"""

def send_email_to_blogger(title, html_content):
    sender = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    recipient = os.environ.get("BLOGGER_EMAIL")

    if not sender or not password or not recipient:
        logger.error("❌ 嚴重錯誤：Email 設定不完整！請檢查 Secrets。")
        logger.error(f"GMAIL_USER: {sender}")
        logger.error(f"BLOGGER_EMAIL: {recipient}")
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
        logger.info(f"✅ Email 發送成功！寄給：{recipient}")
        return True
    except Exception as e:
        logger.error(f"❌ Email 發送失敗 (SMTP Error): {e}")
        return False

def ai_writer(title, summary, keyword):
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key: 
        logger.error("❌ 嚴重錯誤：找不到 GOOGLE_API_KEY")
        return None
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
    
    prompt = f"請將這則新聞改寫成部落格文章，並提到{keyword}。\n新聞標題：{title}\n新聞摘要：{summary}"
    
    logger.info("🤖 正在呼叫 Google Gemini AI...")
    
    for attempt in range(3):
        try:
            res = model.generate_content(prompt)
            if res.text:
                logger.info("✅ AI 生成成功！")
                text = res.text.replace("```html", "").replace("```", "")
                btn = create_shopee_button(keyword)
                return text + btn
        except Exception as e:
            # 這是關鍵！印出錯誤代碼！
            logger.error(f"⚠️ AI 生成失敗 (第 {attempt+1} 次): {e}")
            time.sleep(2)
            
    logger.error("❌ AI 最終放棄治療，無法生成文章。")
    return None

def main():
    logger.info("V29 Debugger Started...")
    rss_url, target_keyword = get_dynamic_rss()
    feed = feedparser.parse(rss_url)
    
    if not feed.entries:
        logger.warning("⚠️ 沒抓到新聞！可能是 RSS 網址有誤或 Google 擋 IP")
        return

    # 強制只跑第一篇
    entry = feed.entries[0]
    logger.info(f"Processing: {entry.title}")
    
    # 開始寫作
    content = ai_writer(entry.title, getattr(entry, "summary", ""), target_keyword)
    
    if content:
        # 寄信
        send_email_to_blogger(f"【{target_keyword}快訊】{entry.title}", content)
    else:
        logger.error("❌ 因為 AI 沒產出內容，所以跳過發信步驟。")

if __name__ == "__main__":
    main()
