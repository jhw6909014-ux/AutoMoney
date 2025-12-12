import os
import time
import random
import logging
import smtplib
import re
import urllib.parse
import feedparser
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, InternalServerError
from email.mime.text import MIMEText
from email.header import Header

# --- V42 CONFIG ---
SHOPEE_ID = "16332290023"
BOT_PERSONA = "3C科技發燒友"
IMG_STYLE = "cyberpunk style, futuristic, product photography"
KEYWORD_POOL = ["iPhone","Android","顯示卡","AI PC","筆電","藍芽耳機","Switch","PS5","智慧手錶","行動電源"]

# 軍用級模型輪替清單
MODEL_ARSENAL = [
    'gemini-1.5-flash',       # 主力輕型戰機 (速度快)
    'gemini-1.5-pro',         # 重型轟炸機 (穩定)
    'gemini-1.0-pro-latest'   # 備用後勤機 (保底)
]

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

def generate_pollinations_url(prompt):
    full_prompt = f"{prompt}, {IMG_STYLE}"
    encoded = urllib.parse.quote(full_prompt)
    seed = random.randint(1, 99999)
    return f"https://image.pollinations.ai/prompt/{encoded}?seed={seed}&width=800&height=450&nologo=true"

def inject_images_into_content(text):
    try:
        def standard_replacer(match):
            img_prompt = match.group(1).strip()
            if not img_prompt: return "" 
            img_url = generate_pollinations_url(img_prompt)
            return f"""<div style="margin: 40px 0; text-align: center;"><img src="{img_url}" alt="{img_prompt}" style="width: 100%; max-width: 800px; border-radius: 12px; box-shadow: 0 8px 20px rgba(0,0,0,0.15);"></div>"""
        text = re.sub(r'\(\(IMG:(.*?)\)\)', standard_replacer, text, flags=re.DOTALL | re.IGNORECASE)
    except: pass
    
    try:
        def failure_replacer(match):
            desc = match.group(1).strip()
            img_url = generate_pollinations_url(desc)
            return f"""<div style="margin: 40px 0; text-align: center;"><img src="{img_url}" alt="AI Illustration" style="width: 100%; max-width: 800px; border-radius: 12px; box-shadow: 0 8px 20px rgba(0,0,0,0.15);"><p style="font-size: 14px; color: #666; margin-top: 10px;">(示意圖)</p></div>"""
        pattern = r'[\(（]AI\s*示意圖[：:](.*?)[\)）]'
        text = re.sub(pattern, failure_replacer, text, flags=re.DOTALL | re.IGNORECASE)
    except: pass
    return text

def beautify_and_clean_html(html_text):
    html_text = re.sub(r'^###s+(.*)$', r'<h2>\1</h2>', html_text, flags=re.MULTILINE)
    html_text = re.sub(r'^##s+(.*)$', r'<h2>\1</h2>', html_text, flags=re.MULTILINE)
    html_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html_text)

    styled_h2 = '<h2 style="color: #0369a1; font-size: 24px; margin-top: 40px; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #e0f2fe; font-weight: bold;">'
    html_text = html_text.replace('<h2>', styled_h2)
    
    styled_p = '<p style="font-size: 17px; line-height: 1.9; margin-bottom: 25px; color: #334155;">'
    html_text = html_text.replace('<p>', styled_p)
    
    styled_ul = '<ul style="margin-bottom: 25px; padding-left: 20px; list-style-type: disc;">'
    html_text = html_text.replace('<ul>', styled_ul)
    styled_li = '<li style="margin-bottom: 10px; font-size: 17px; line-height: 1.6;">'
    html_text = html_text.replace('<li>', styled_li)
    
    if '<table>' in html_text or '|' in html_text:
        styled_table_start = """
        <div style="overflow-x: auto; margin: 30px 0;">
            <table border="1" cellspacing="0" cellpadding="8" style="width: 100%; border-collapse: collapse; border: 2px solid #333; font-size: 16px;">
        """
        html_text = re.sub(r'<table[^>]*>', styled_table_start, html_text)
        html_text = html_text.replace('<th>', '<th style="background-color: #f1f5f9; padding: 12px; border: 1px solid #94a3b8; font-weight: bold;">')
        html_text = html_text.replace('<td>', '<td style="padding: 12px; border: 1px solid #cbd5e1;">')
        
        if '<div style="overflow-x: auto;' in html_text and '</table>' in html_text:
             if '</table></div>' not in html_text:
                html_text = html_text.replace('</table>', '</table></div>')
                
    return html_text

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

# --- V42 核心：軍用級抗 429 邏輯 ---
def generate_content_with_retry(prompt):
    """
    輪詢多個模型，遇到 429 錯誤自動切換並冷卻
    """
    for model_name in MODEL_ARSENAL:
        try:
            logger.info(f"🚀 嘗試使用模型: {model_name}")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response
            
        except ResourceExhausted:
            logger.warning(f"⚠️ 模型 {model_name} 額度耗盡 (429)。啟動戰術冷卻 30秒...")
            time.sleep(30) # 強制冷卻 30 秒
            logger.info("🔄 切換至下一備用模型...")
            continue # 嘗試下一個模型
            
        except (ServiceUnavailable, InternalServerError) as e:
            logger.error(f"⚠️ Google 服務端錯誤 ({e})。等待 10秒...")
            time.sleep(10)
            continue
            
        except Exception as e:
            logger.error(f"❌ 未知錯誤: {e}")
            break # 非連線錯誤，直接停止以免無限迴圈

    logger.error("❌ 所有模型皆無法使用，任務中止。")
    return None

def ai_writer(title, summary, keyword):
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key: return None
    genai.configure(api_key=api_key)

    prompt = f"""
    你是一位【{BOT_PERSONA}】。
    文章主題：【{keyword}】。
    新聞標題：{title}
    
    請撰寫一篇部落格文章。
    
    【極重要格式指令】：
    1. **請直接輸出 HTML 原始碼**。
    2. **嚴禁使用 Markdown**。
    3. 標題請用 <h2>...</h2>。
    4. 段落請用 <p>...</p>。
    5. 表格請用 <table>...</table>。
    6. 圖片請插入 ((IMG: English Description))。
    
    【內容結構】：
    1. <h2>副標題</h2>
    2. <p>內文段落...</p>
    3. <table>規格/分析表格</table>
    4. <h2>結論</h2>
    """
    
    # 呼叫軍用級生成函式
    res = generate_content_with_retry(prompt)
    
    if res and res.text:
        raw_html = res.text.replace("```html", "").replace("```", "")
        html_with_img = inject_images_into_content(raw_html)
        final_html = beautify_and_clean_html(html_with_img)
        hero_img = get_hero_image(keyword)
        btn = create_shopee_button(keyword)
        wrapper = f"""<div style="font-family: Arial, Helvetica, sans-serif; color: #333; max-width: 100%;">{final_html}</div>"""
        return hero_img + wrapper + btn
    
    return None

def main():
    logger.info("V42 Military Bot Started...")
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
