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

# --- V36 CONFIG ---
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

def create_shopee_button(keyword):
    safe_keyword = urllib.parse.quote(keyword)
    url = f"https://shopee.tw/search?keyword={safe_keyword}&utm_source=affiliate&utm_campaign={SHOPEE_ID}"
    
    return f"""
    <div style="clear: both; margin-top: 50px; padding: 25px; background-color: #f8fafc; border-radius: 12px; text-align: center; border: 1px solid #e2e8f0;">
        <h3 style="margin-bottom: 15px; font-size: 19px; color: #1e293b; font-weight: bold;">💡 讀者專屬優惠</h3>
        <a href="{url}" target="_blank" rel="nofollow" 
           style="display: inline-block; background-color: #8b5cf6; color: white; padding: 16px 36px; border-radius: 50px; text-decoration: none; font-weight: bold; font-size: 18px; box-shadow: 0 4px 15px rgba(139,92,246,0.4); transition: transform 0.2s;">
           🛍️ 點此查看「{keyword}」最新價格
        </a>
        <p style="margin-top: 12px; font-size: 13px; color: #64748b;">(點擊前往蝦皮購物)</p>
    </div>
    """

# --- V36 新增：標題淨化函式 ---
def clean_rss_title(title):
    """
    移除標題末端的來源標示 (如 ' - 自由電子報' 或 ' | TechBang')
    """
    # 移除 ' - ' 後面的所有內容
    title = title.split(" - ")[0]
    # 移除 ' | ' 後面的所有內容
    title = title.split(" | ")[0]
    return title.strip()

def style_table_html(html_text):
    styled_table_start = """
    <div style="overflow-x: auto; margin: 20px 0;">
        <table border="1" cellspacing="0" cellpadding="5" style="width: 100%; border-collapse: collapse; border: 1px solid #333; font-size: 16px;">
    """
    html_text = re.sub(r'<table[^>]*>', styled_table_start, html_text)
    
    styled_th = '<th style="background-color: #f3e8ff; color: #2e1065; font-weight: bold; padding: 12px; border: 1px solid #333; text-align: left;">'
    html_text = re.sub(r'<th[^>]*>', styled_th, html_text)
    
    styled_td = '<td style="padding: 12px; border: 1px solid #333; color: #4c1d95;">'
    html_text = re.sub(r'<td[^>]*>', styled_td, html_text)
    
    if '<div style="overflow-x: auto;' in html_text:
        html_text = html_text.replace('</table>', '</table></div>')
        
    return html_text

def inject_images_into_content(text):
    try:
        def replacer(match):
            try:
                img_prompt = match.group(1).strip()
                if not img_prompt: return "" 
                
                full_prompt = f"{img_prompt}, {IMG_STYLE}"
                encoded = urllib.parse.quote(full_prompt)
                seed = random.randint(1, 99999)
                img_url = f"https://image.pollinations.ai/prompt/{encoded}?seed={seed}&width=800&height=450&nologo=true"
                
                return f"""
                <div style="margin: 30px 0; text-align: center;">
                    <img src="{img_url}" alt="{img_prompt}" style="width: 100%; max-width: 800px; border-radius: 12px; box-shadow: 0 8px 20px rgba(0,0,0,0.15);">
                    <p style="font-size: 13px; color: #888; margin-top: 8px;">(AI 示意圖：{img_prompt})</p>
                </div>
                """
            except:
                return ""

        pattern = r'\(\(IMG:(.*?)\)\)'
        new_text = re.sub(pattern, replacer, text, flags=re.DOTALL | re.IGNORECASE)
        return new_text
        
    except:
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

    # --- V36 指令修正：副標題策略 ---
    prompt = f"""
    你是一位【{BOT_PERSONA}】。
    文章主題：【{keyword}】。
    新聞標題：{title}
    
    請撰寫一篇部落格文章。
    
    【結構指令 (重要)】：
    1. 文章開頭：請自行撰寫一個「吸引人的副標題 (Subtitle)」，使用 <h2> 標籤包住。
       (注意：不要重複新聞原本的標題，請發揮創意改寫得更聳動)
    2. 圖片：在副標題下方，以及文章中間、結尾前，插入圖片指令： ((IMG: 圖片描述))
    3. 內文：針對新聞內容進行分析與個人評論。
    4. 表格：必須包含一個 HTML <table> 表格 (比較規格或優缺點)。
    
    【HTML 格式】：
    使用 <h2>, <p>, <table> 等標籤排版。不要輸出 markdown。
    """
    
    for attempt in range(3):
        try:
            res = model.generate_content(prompt)
            if res.text:
                raw_html = res.text.replace("```html", "").replace("```", "")
                html_with_img = inject_images_into_content(raw_html)
                final_content = style_table_html(html_with_img)
                btn = create_shopee_button(keyword)
                return final_content + btn
        except Exception as e:
            logger.error(f"⚠️ Error: {e}")
            time.sleep(2)
    return None

def main():
    logger.info("V36 Title Fix Started...")
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
        
        # --- V36 應用標題淨化 ---
        clean_title = clean_rss_title(entry.title)
        
        content = ai_writer(clean_title, getattr(entry, "summary", ""), target_keyword)
        
        if content:
            # Email 標題只使用乾淨的 RSS 標題 + Emoji
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
