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
SHOPEE_ID = "16332290023"
BOT_PERSONA = "專業3C科技發燒友"
KEYWORD_POOL = ["筆電", "顯示卡", "iPhone", "AI PC", "電競螢幕", "機械鍵盤"]

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
    return f"""<br><div style="text-align:center; margin-top:20px;"><a href="{url}" style="background-color:#ea580c;color:white;padding:12px 24px;border-radius:50px;text-decoration:none;font-weight:bold;font-size:16px;">🔥 查看「{keyword}」最新優惠價格</a></div><br>"""

def send_email_to_blogger(title, html_content):
    sender = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    recipient = os.environ.get("BLOGGER_EMAIL")

    if not sender or not password or not recipient:
        logger.error("❌ Email 設定不完整")
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
        logger.error(f"❌ Email 發送失敗: {e}")
        return False

def ai_writer(title, summary, keyword):
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key: 
        logger.error("❌ 找不到 GOOGLE_API_KEY")
        return None
    
    genai.configure(api_key=api_key)
    
    # --- 修正：使用 gemini-1.5-flash 並配合 requirements.txt 更新 ---
    model = genai.GenerativeModel('gemini-1.5-flash')
    # -----------------------------------------------------------
    
    prompt = f"你是一位{BOT_PERSONA}。請將這則新聞改寫成一篇繁體中文部落格文章，重點介紹{keyword}的相關資訊。\n\n新聞標題：{title}\n新聞摘要：{summary}\n\n要求：\n1. 語氣專業且生動。\n2. 必須包含一個 HTML 表格比較相關產品規格或優缺點。\n3. 文章結尾要引導讀者查看優惠。"
    
    logger.info("🤖 呼叫 Google Gemini 1.5 Flash...")
    
    for attempt in range(3):
        try:
            res = model.generate_content(prompt)
            if res.text:
                logger.info("✅ AI 生成成功！")
                text = res.text.replace("```html", "").replace("```", "")
                btn = create_shopee_button(keyword)
                return text + btn
        except Exception as e:
            logger.error(f"⚠️ AI 生成失敗 (第 {attempt+1} 次): {e}")
            time.sleep(2)
            
    return None

def main():
    logger.info("V29 Fixed Started...")
    rss_url, target_keyword = get_dynamic_rss()
    feed = feedparser.parse(rss_url)
    
    if not feed.entries:
        logger.warning("⚠️ 沒抓到新聞")
        return

    # 隨機挑選一篇新聞，避免每次都抓到同一篇置頂
    entry = feed.entries[0]
    logger.info(f"Processing: {entry.title}")
    
    content = ai_writer(entry.title, getattr(entry, "summary", ""), target_keyword)
    
    if content:
        send_email_to_blogger(f"【{target_keyword}情報】{entry.title}", content)
    else:
        logger.error("❌ AI 無法產出內容，跳過。")

if __name__ == "__main__":
    main()
