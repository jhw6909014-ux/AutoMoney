import os
import time
import random
import logging
import smtplib
import re
import urllib.parse
import feedparser
import google.generativeai as genai
from email.mime.text import MIMEText
from email.header import Header

# --- V38 CONFIG ---
SHOPEE_ID = "16332290023"
BOT_PERSONA = "3C科技發燒友"
IMG_STYLE = "cyberpunk style, futuristic, product photography"
KEYWORD_POOL = ["iPhone","Android","顯示卡","AI PC","筆電","藍芽耳機","Switch","PS5","智慧手錶","行動電源"]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def get_dynamic_rss():
    target_keyword = random.choice(KEYWORD_POOL)
    logger.info(f"🎯 鎖定關鍵字: {target_keyword}")
    encoded = urllib.parse.quote(target_keyword)
    rss_url = f"https://news.google.com/rss/search?q={encoded}+when:1d&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    return rss_url, target_keyword

def clean_rss_title(title):
    title = title.split(" - ")[0]
    title = title.split(" | ")[0]
    return title.strip()

def create_shopee_button(keyword):
    safe_keyword = urllib.parse.quote(keyword)
    url = f"https://shopee.tw/search?keyword={safe_keyword}&utm_source=affiliate&utm_campaign={SHOPEE_ID}"
    
    # 這裡保留 V37 的動態按鈕
    css_animation = """
    <style>
    @keyframes pulse-red {
        0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.7); }
        70% { transform: scale(1.05); box-shadow: 0 0 0 10px rgba(220, 38, 38, 0); }
        100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(220, 38, 38, 0); }
    }
    .shopee-btn { animation: pulse-red 2s infinite; }
    </style>
    """
    
    return css_animation + f"""
    <div style="clear: both; margin: 60px 0; padding: 40px 20px; background-color: #fef2f2; border: 2px dashed #ef4444; border-radius: 15px; text-align: center;">
        <h3 style="margin-bottom: 20px; font-size: 22px; color: #991b1b; font-weight: 900;">🔥 限時優惠情報</h3>
        <p style="margin-bottom: 20px; color: #b91c1c; font-size: 16px;">正在尋找 <b>{keyword}</b> 嗎？立即查看今日最殺價格！</p>
        <a href="{url}" target="_blank" rel="nofollow" class="shopee-btn"
           style="display: inline-block; background-color: #dc2626; color: white; padding: 20px 50px; border-radius: 50px; text-decoration: none; font-weight: 900; font-size: 24px; box-shadow: 0 5px 20px rgba(220,38,38,0.5);">
           🚀 點此前往蝦皮賣場
        </a>
        <p style="margin-top: 15px; font-size: 14px; color: #7f1d1d;">(官網/商城正品保證)</p>
    </div>
    """

def get_hero_image(keyword):
    try:
        full_prompt = f"Product shot of {keyword}, {IMG_STYLE}, cinematic lighting, 8k, highly detailed"
        encoded = urllib.parse.quote(full_prompt)
        seed = random.randint(1, 99999)
        img_url = f"https://image.pollinations.ai/prompt/{encoded}?seed={seed}&width=1024&height=576&nologo=true"
        return f"""<div style="margin-bottom: 30px; text-align: center;"><img src="{img_url}" alt="{keyword}" style="width: 100%; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.2);"></div>"""
    except:
        return ""

def style_table_html(html_text):
    styled_table_start = """
    <div style="overflow-x: auto; margin: 30px 0;">
        <table border="1" cellspacing="0" cellpadding="8" style="width: 100%; border-collapse: collapse; border: 2px solid #333; font-size: 16px;">
    """
    html_text = re.sub(r'<table[^>]*>', styled_table_start, html_text)
    
    styled_th = '<th style="background-color: #f3f4f6; color: #111; font-weight: bold; padding: 15px; border: 1px solid #333; text-align: left;">'
    html_text = re.sub(r'<th[^>]*>', styled_th, html_text)
    
    styled_td = '<td style="padding: 15px; border: 1px solid #333; color: #333;">'
    html_text = re.sub(r'<td[^>]*>', styled_td, html_text)
    
    if '<div style="overflow-x: auto;' in html_text:
        html_text = html_text.replace('</table>', '</table></div>')
    return html_text

# --- V38 核心修正：文字轉圖片邏輯 ---
def generate_pollinations_url(prompt):
    full_prompt = f"{prompt}, {IMG_STYLE}"
    encoded = urllib.parse.quote(full_prompt)
    seed = random.randint(1, 99999)
    return f"https://image.pollinations.ai/prompt/{encoded}?seed={seed}&width=800&height=450&nologo=true"

def inject_images_into_content(text):
    # 1. 處理正確的 ((IMG:...)) 格式
    try:
        def standard_replacer(match):
            img_prompt = match.group(1).strip()
            if not img_prompt: return "" 
            img_url = generate_pollinations_url(img_prompt)
            return f"""
            <div style="margin: 40px 0; text-align: center;">
                <img src="{img_url}" alt="{img_prompt}" style="width: 100%; max-width: 800px; border-radius: 12px; box-shadow: 0 8px 20px rgba(0,0,0,0.15);">
            </div>
            """
        
        text = re.sub(r'\(\(IMG:(.*?)\)\)', standard_replacer, text, flags=re.DOTALL | re.IGNORECASE)
    except: pass

    # 2. V38 掃雷：處理錯誤的 (AI 示意圖：...) 格式
    # 支援半形括號 () 和全形括號 （）
    try:
        def failure_replacer(match):
            # 抓取中文描述
            desc = match.group(1).strip()
            logger.info(f"🔧 修復錯誤格式圖片: {desc}")
            
            # 使用描述生成圖片 (Pollinations 支援部分中文，或透過 Prompt 加強)
            # 為了保險，我們把 "style" 加在後面
            img_url = generate_pollinations_url(desc)
            
            return f"""
            <div style="margin: 40px 0; text-align: center;">
                <img src="{img_url}" alt="AI Illustration" style="width: 100%; max-width: 800px; border-radius: 12px; box-shadow: 0 8px 20px rgba(0,0,0,0.15);">
                <p style="font-size: 14px; color: #666; margin-top: 10px; font-style: italic;">(示意圖)</p>
            </div>
            """
        
        # Regex 說明: 
        # [\(（] : 匹配半形或全形左括號
        # AI\s*示意圖 : 匹配 AI 示意圖 (中間允許空白)
        # [：:] : 匹配全形或半形冒號
        # (.*?) : 抓取內容
        # [\)）] : 匹配半形或全形右括號
        pattern = r'[\(（]AI\s*示意圖[：:](.*?)[\)）]'
        text = re.sub(pattern, failure_replacer, text, flags=re.DOTALL | re.IGNORECASE)
        
    except Exception as e:
        logger.error(f"掃雷失敗: {e}")

    return text

def send_email_to_blogger(title, html_content):
    sender = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    recipient = os.environ.get("BLOGGER_EMAIL")
    if not sender or not password or not recipient: return False
    
    msg = MIMEText(html_content, 'html', 'utf-8')
    msg['Subject'] = Header(title, 'utf-8')
    msg['From'] = sender
    msg['To'] = recipient
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        logger.info("✅ Email 發送成功！")
        return True
    except Exception as e:
        logger.error(f"❌ Email 發送失敗: {e}")
        return False

def ai_writer(title, summary, keyword):
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key: return None
    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
    except:
        model = genai.GenerativeModel('gemini-pro')

    prompt = f"""
    你是一位【{BOT_PERSONA}】。
    文章主題：【{keyword}】。
    新聞標題：{title}
    
    請撰寫一篇部落格文章。
    
    【重要指令】：
    1. 圖片：請儘量使用 ((IMG: English Description)) 格式。
    2. 表格：必須包含 <table>。
    3. 結尾：要有購買建議。
    """
    
    for attempt in range(3):
        try:
            res = model.generate_content(prompt)
            if res.text:
                raw_html = res.text.replace("```html", "").replace("```", "")
                
                # 1. 注入 & 修復圖片 (V38 重點)
                html_with_img = inject_images_into_content(raw_html)
                
                # 2. 首圖
                hero_img = get_hero_image(keyword)
                
                # 3. 表格
                styled_html = style_table_html(html_with_img)
                
                # 4. 按鈕
                btn = create_shopee_button(keyword)
                
                return hero_img + styled_html + btn
        except Exception as e:
            logger.error(f"⚠️ Error: {e}")
            time.sleep(2)
    return None

def main():
    logger.info("V38 Final Bot Started...")
    rss_url, target_keyword = get_dynamic_rss()
    try:
        feed = feedparser.parse(rss_url)
        if not feed.entries: return
        history = []
        if os.path.exists("history.txt"):
            with open("history.txt", "r") as f: history = f.read().splitlines()
        candidates = [e for e in feed.entries if e.link not in history]
        if not candidates: return
        
        entry = random.choice(candidates[:3])
        logger.info(f"Processing: {entry.title}")
        clean_title = clean_rss_title(entry.title)
        
        content = ai_writer(clean_title, getattr(entry, "summary", ""), target_keyword)
        
        if content:
            emojis = ["🔥", "⚡", "💡", "🚀", "📢"]
            emo = random.choice(emojis)
            email_title = f"{emo} 【{target_keyword}】{clean_title}"
            success = send_email_to_blogger(email_title, content)
            if success:
                with open("history.txt", "a") as f: f.write(f"{entry.link}\n")
    except Exception as e:
        logger.error(f"Main Error: {e}")

if __name__ == "__main__":
    main()
