import os
import time
import random
import logging
import smtplib
import urllib.parse
import feedparser
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
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
    # 使用 Google News RSS
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
    
    # 印出版本以確認環境 (除錯用)
    logger.info(f"📚 Google GenAI Library Version: {genai.__version__}")

    genai.configure(api_key=api_key)
    
    # 設定安全過濾器，避免因為新聞內容稍微敏感就被 AI 拒絕生成
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    # 指定模型，若 flash 版本有問題，可以改用 gemini-1.5-flash-latest 或 gemini-pro
    model_name = 'gemini-1.5-flash'
    model = genai.GenerativeModel(model_name, safety_settings=safety_settings)
    
    prompt = f"""
    你是一位{BOT_PERSONA}。請將這則新聞改寫成一篇繁體中文部落格文章，重點介紹{keyword}的相關資訊。
    
    新聞標題：{title}
    新聞摘要：{summary}
    
    要求：
    1. 標題要吸引人 (SEO友善)。
    2. 語氣專業且生動。
    3. 內容必須包含 HTML 格式 (使用 <p>, <h3>, <ul>, <li> 等標籤)。
    4. 必須包含一個 HTML 表格 (<table>) 比較相關產品規格或優缺點 (若無具體數據請根據常識推斷)。
    5. 文章結尾請加上一句引導語，鼓勵讀者點擊下方按鈕查看價格。
    6. 不要輸出 ```html 標記，直接輸出 HTML 程式碼。
    """
    
    logger.info(f"🤖 呼叫 Google Gemini ({model_name})...")
    
    for attempt in range(3):
        try:
            res = model.generate_content(prompt)
            # 檢查回應是否被安全設定擋下
            if res.text:
                logger.info("✅ AI 生成成功！")
                text = res.text.replace("```html", "").replace("```", "")
                btn = create_shopee_button(keyword)
                return text + btn
            else:
                logger.warning(f"⚠️ AI 回應為空 (可能是安全過濾): {res.prompt_feedback}")
        except Exception as e:
            logger.error(f"⚠️ AI 生成失敗 (第 {attempt+1} 次): {e}")
            # 如果是 404，可能是模型名稱錯誤，嘗試列出可用模型 (僅在 Log 顯示)
            if "404" in str(e) and attempt == 0:
                try:
                    logger.info("列出可用模型以供除錯:")
                    for m in genai.list_models():
                        if 'generateContent' in m.supported_generation_methods:
                            logger.info(f"- {m.name}")
                except:
                    pass
            time.sleep(2)
            
    return None

def main():
    logger.info("V30 Fixed Logic Started...")
    rss_url, target_keyword = get_dynamic_rss()
    
    try:
        feed = feedparser.parse(rss_url)
    except Exception as e:
        logger.error(f"❌ RSS 解析失敗: {e}")
        return

    if not feed.entries:
        logger.warning("⚠️ 沒抓到新聞")
        return

    # 隨機挑選前 3 篇的其中一篇，增加隨機性
    target_entry_index = random.randint(0, min(2, len(feed.entries)-1))
    entry = feed.entries[target_entry_index]
    
    logger.info(f"Processing: {entry.title}")
    
    # 取得摘要，若無摘要則用標題代替
    summary_text = getattr(entry, "summary", entry.title)
    
    content = ai_writer(entry.title, summary_text, target_keyword)
    
    if content:
        send_email_to_blogger(f"【{target_keyword}快訊】{entry.title}", content)
    else:
        logger.error("❌ AI 無法產出內容，跳過。")

if __name__ == "__main__":
    main()
