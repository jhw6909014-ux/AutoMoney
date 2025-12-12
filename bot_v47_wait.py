import os
import time
import random
import logging
import smtplib
import re
import urllib.parse
import feedparser
import google.generativeai as genai
# 引入錯誤類型
from google.api_core.exceptions import ResourceExhausted
from email.mime.text import MIMEText
from email.header import Header

# --- V47 CONFIG ---
SHOPEE_ID = "16332290023"
BOT_PERSONA = "專業部落客"
IMG_STYLE = "realistic, 8k, high quality"
KEYWORD_POOL = ["iPhone","Android","顯示卡","AI PC","筆電","藍芽耳機","Switch","PS5","智慧手錶","行動電源"]

# V47 策略：既然 gemini-flash-latest 存在但會限流，我們就鎖定它
MODEL_LIST = [
    'gemini-flash-latest',   # 這是你 Log 中唯一活著的模型
    'gemini-1.5-flash-latest', 
    'gemini-pro'
]

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
    css = """<style>@keyframes pulse{0%{transform:scale(1);}50%{transform:scale(1.05);}100%{transform:scale(1);}}.btn{animation:pulse 2s infinite;}</style>"""
    return css + f"""<div style="margin:50px 0;text-align:center;"><a href="{url}" class="btn" style="background:#0074D9;color:white;padding:15px 30px;border-radius:50px;text-decoration:none;font-weight:bold;font-size:20px;">🔥 查看 {keyword} 優惠</a></div>"""

def get_hero_image(keyword):
    try:
        encoded = urllib.parse.quote(f"{keyword}, {IMG_STYLE}")
        seed = random.randint(1, 9999)
        url = f"https://image.pollinations.ai/prompt/{encoded}?seed={seed}&width=800&height=450&nologo=true"
        return f'<div style="text-align:center;margin-bottom:30px;"><img src="{url}" style="width:100%;border-radius:10px;"></div>'
    except: return ""

def generate_with_retry(prompt):
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
    
    for model_name in MODEL_LIST:
        logger.info(f"🚀 V47 鎖定模型: {model_name}")
        model = genai.GenerativeModel(model_name)
        
        # 對同一個模型進行最多 3 次嘗試 (包含冷卻時間)
        for attempt in range(3):
            try:
                response = model.generate_content(prompt)
                if response and response.text:
                    logger.info("✅ 生成成功！")
                    return response
            except ResourceExhausted:
                # 這是 V47 的核心：遇到 429 不換模型，而是等待
                wait_time = 70  # Google 說 31 秒，我們等 70 秒以防萬一
                logger.warning(f"⚠️ {model_name} 額度滿了 (429)。賴皮等待中... ({wait_time}秒)")
                time.sleep(wait_time)
                logger.info("⏰ 起床重試...")
                continue # 繼續迴圈，重試同一個模型
            except Exception as e:
                # 如果是 404 或其他錯誤，才換下一個模型
                logger.error(f"❌ {model_name} 發生非額度錯誤: {e} -> 換下一個")
                break 
    return None

def main():
    logger.info("=================================")
    logger.info("⏳ V47 WAIT STRATEGY START ⏳")
    logger.info("=================================")
    
    rss_url, target_keyword = get_dynamic_rss()
    try:
        feed = feedparser.parse(rss_url)
        if not feed.entries: return
        entry = feed.entries[0]
        logger.info(f"Processing: {entry.title}")
        
        prompt = f"""
        你是一位{BOT_PERSONA}。主題：{target_keyword}。新聞：{entry.title}。
        請直接輸出 HTML (不要 Markdown)。
        結構：<h2>副標題</h2><p>內文</p><table>規格表</table><h2>結論</h2>
        圖片插入 ((IMG: English Desc))
        """
        
        res = generate_with_retry(prompt)
        
        if res:
            html = res.text.replace("```html", "").replace("```", "")
            
            # 圖片注入
            def replacer(m): 
                return f'<img src="https://image.pollinations.ai/prompt/{urllib.parse.quote(m.group(1))}?nologo=true" style="width:100%;border-radius:10px;margin:20px 0;">'
            html = re.sub(r'\(\(IMG:(.*?)\)\)', replacer, html)
            
            # CSS 暴力注入 (確保排版)
            html = html.replace("<p>", '<p style="margin-bottom:25px;line-height:2.0;font-size:18px;">')
            html = html.replace("<h2>", '<h2 style="color:#0074D9;margin-top:40px;font-size:24px;border-bottom:2px solid #ddd;padding-bottom:10px;">')
            if "<table>" in html:
                html = html.replace("<table>", '<div style="overflow-x:auto;"><table border="1" style="width:100%;border-collapse:collapse;margin:30px 0;border:2px solid #333;">')
                html = html.replace("</table>", '</table></div>')
                html = html.replace("td>", 'td style="padding:15px;border:1px solid #ccc;">')
                html = html.replace("th>", 'th style="background:#f4f4f4;padding:15px;border:1px solid #333;">')

            final = get_hero_image(target_keyword) + html + create_shopee_button(target_keyword)
            
            sender = os.environ.get("GMAIL_USER")
            pwd = os.environ.get("GMAIL_APP_PASSWORD")
            to = os.environ.get("BLOGGER_EMAIL")
            
            msg = MIMEText(final, 'html', 'utf-8')
            msg['Subject'] = Header(f"🔥 {entry.title}", 'utf-8')
            msg['From'] = sender
            msg['To'] = to
            
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                s.login(sender, pwd)
                s.send_message(msg)
            logger.info("✅ 發送成功")
            
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    main()
