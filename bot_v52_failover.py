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

# --- V52 CONFIGURATION ---
SHOPEE_ID = "16332290023"
BOT_PERSONA = "專業部落客"
IMG_STYLE = "cyberpunk, futuristic, high tech"
KEYWORD_POOL = ["iPhone","Android","AI手機","筆電","藍芽耳機","Switch","PS5","智慧手錶","行動電源","機械鍵盤","顯示卡","空拍機"]

# 強制備用模型 (保底用)
BACKUP_MODELS = ['gemini-1.5-pro', 'gemini-pro', 'gemini-1.0-pro']

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def get_dynamic_rss():
    target_keyword = random.choice(KEYWORD_POOL)
    logger.info(f"🎯 鎖定關鍵字: {target_keyword}")
    encoded = urllib.parse.quote(target_keyword)
    rss_url = f"https://news.google.com/rss/search?q={encoded}+when:1d&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    return rss_url, target_keyword

# --- V52 CORE: SMART ROUTING ---
def get_optimized_model_list():
    """
    1. 嘗試動態獲取模型
    2. 將獲取的模型與備用模型合併 (去重複)
    3. 確保多樣性
    """
    valid_models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                valid_models.append(m.name)
    except:
        pass # 如果 API 列表失敗，直接用備用清單

    # 合併清單，並移除 'models/' 前綴以便統一處理 (如果有的話)
    # Google API 有時回傳 'models/gemini-pro' 有時是 'gemini-pro'
    # 這裡我們統一使用完整名稱
    
    # 確保備用模型也在清單中 (增加成功率)
    for backup in BACKUP_MODELS:
        # 檢查是否已存在 (模糊比對)
        found = False
        for valid in valid_models:
            if backup in valid:
                found = True
                break
        if not found:
            valid_models.append(backup) # 強制加入備用模型

    # 排序：優先嘗試 1.5-flash (快), 然後 pro
    valid_models.sort(key=lambda x: (
        0 if 'flash' in x and '1.5' in x else
        1 if 'flash' in x else
        2 if '1.5' in x else
        3
    ))
    
    logger.info(f"📋 V52 攻擊清單: {valid_models}")
    return valid_models

def create_shopee_button(keyword):
    safe_keyword = urllib.parse.quote(keyword)
    url = f"https://shopee.tw/search?keyword={safe_keyword}&utm_source=affiliate&utm_campaign={SHOPEE_ID}"
    css = """<style>@keyframes pulse{0%{transform:scale(1);}50%{transform:scale(1.05);}100%{transform:scale(1);}}.btn{animation:pulse 2s infinite;}</style>"""
    return css + f"""<div style="margin:50px 0;text-align:center;"><a href="{url}" class="btn" style="background:#008f7a;color:white;padding:15px 30px;border-radius:50px;text-decoration:none;font-weight:bold;font-size:20px;">🔥 查看 {keyword} 最新優惠</a></div>"""

def get_hero_image(keyword):
    try:
        encoded = urllib.parse.quote(f"{keyword}, {IMG_STYLE}")
        seed = random.randint(1, 9999)
        url = f"https://image.pollinations.ai/prompt/{encoded}?seed={seed}&width=800&height=450&nologo=true"
        return f'<div style="text-align:center;margin-bottom:30px;"><img src="{url}" style="width:100%;border-radius:10px;"></div>'
    except: return ""

def generate_with_fast_failover(prompt):
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
    
    # 取得混合模型清單
    models_to_try = get_optimized_model_list()
    
    for model_name in models_to_try:
        logger.info(f"🚀 V52 嘗試模型: {model_name}")
        
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            
            if response and response.text:
                logger.info(f"✅ {model_name} 生成成功！")
                return response
        
        except ResourceExhausted:
            # V52 核心：不等待，直接換下一個
            logger.warning(f"⚠️ {model_name} 配額已滿 (429)。不等待，立即切換下一位！")
            time.sleep(5) # 僅做禮貌性冷卻
            continue # 跳出本次嘗試，進入 for 迴圈的下一個 model
        
        except Exception as e:
            logger.error(f"❌ {model_name} 錯誤: {e} -> 切換下一位")
            time.sleep(2)
            continue
            
    return None

def main():
    logger.info("====================================")
    logger.info("⚡ V52 FAST FAILOVER BOT STARTED ⚡")
    logger.info("====================================")
    
    rss_url, target_keyword = get_dynamic_rss()
    try:
        feed = feedparser.parse(rss_url)
        if not feed.entries: return
        entry = feed.entries[0]
        logger.info(f"Processing: {entry.title}")
        
        prompt = f"""
        你是一位{BOT_PERSONA}。主題：{target_keyword}。新聞：{entry.title}。
        任務：請根據新聞內容，寫一篇吸引人的部落格文章。
        
        【HTML 格式指令】：
        1. **直接輸出 HTML** (不要 Markdown)。
        2. 使用 <h2> 標籤作為副標題。
        3. 使用 <p> 標籤包裹內文段落。
        4. 必須包含一個 HTML <table> 表格。
        5. 圖片位置請插入: ((IMG: English Description))
        """
        
        res = generate_with_fast_failover(prompt)
        
        if res:
            html = res.text.replace("```html", "").replace("```", "")
            
            def replacer(m): 
                return f'<img src="https://image.pollinations.ai/prompt/{urllib.parse.quote(m.group(1))}?nologo=true" style="width:100%;border-radius:10px;margin:20px 0;">'
            html = re.sub(r'\(\(IMG:(.*?)\)\)', replacer, html)
            
            html = html.replace("<p>", '<p style="margin-bottom:25px;line-height:2.0;font-size:18px;color:#333;">')
            html = html.replace("<h2>", '<h2 style="color:#008f7a;margin-top:40px;font-size:24px;border-bottom:2px solid #00ffcc;padding-bottom:10px;font-weight:bold;">')
            if "<table>" in html:
                html = html.replace("<table>", '<div style="overflow-x:auto;"><table border="1" style="width:100%;border-collapse:collapse;margin:30px 0;border:2px solid #333;">')
                html = html.replace("</table>", '</table></div>')
                html = html.replace("td>", 'td style="padding:15px;border:1px solid #ccc;">')
                html = html.replace("th>", 'th style="background:#f0fdfa;padding:15px;border:1px solid #333;font-weight:bold;">')

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
        logger.error(f"Main Error: {e}")

if __name__ == "__main__":
    main()
