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

# --- V51 CONFIGURATION ---
SHOPEE_ID = "16332290023"
BOT_PERSONA = "專業部落客"
IMG_STYLE = "cyberpunk, futuristic, high tech"
KEYWORD_POOL = ["iPhone","Android","AI手機","筆電","藍芽耳機","Switch","PS5","智慧手錶","行動電源","機械鍵盤","顯示卡","空拍機"]

# 移除硬編碼模型列表，改用動態發現
FALLBACK_MODEL = 'gemini-pro' # 萬一真的動態失敗，才用這個

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def get_dynamic_rss():
    target_keyword = random.choice(KEYWORD_POOL)
    logger.info(f"🎯 鎖定關鍵字: {target_keyword}")
    encoded = urllib.parse.quote(target_keyword)
    rss_url = f"https://news.google.com/rss/search?q={encoded}+when:1d&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    return rss_url, target_keyword

# --- V51 CORE: DYNAMIC MODEL DISCOVERY ---
def get_working_models():
    """
    直接詢問 Google API 當前可用的模型，避免 404 猜測。
    """
    logger.info("🔍 V51: 正在執行模型自我發現 (Service Discovery)...")
    valid_models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                valid_models.append(m.name)
        
        if not valid_models:
            logger.warning("⚠️ 無法獲取模型列表，使用 Fallback。")
            return [FALLBACK_MODEL]
            
        # 排序邏輯：優先 Flash (速度)，其次 Pro
        # 因為 list_models 回傳的是 'models/gemini-1.5-flash' 格式，我們需要保留完整名稱
        valid_models.sort(key=lambda x: (
            0 if 'flash' in x and '1.5' in x else
            1 if 'flash' in x else
            2 if '1.5' in x else
            3
        ))
        
        logger.info(f"✅ 發現可用模型 (已排序): {valid_models}")
        return valid_models
        
    except Exception as e:
        logger.error(f"❌ 模型發現失敗: {e}")
        return [FALLBACK_MODEL]

def create_shopee_button(keyword):
    safe_keyword = urllib.parse.quote(keyword)
    url = f"https://shopee.tw/search?keyword={safe_keyword}&utm_source=affiliate&utm_campaign={SHOPEE_ID}"
    css = """<style>@keyframes pulse{0%{transform:scale(1);}50%{transform:scale(1.05);}100%{transform:scale(1);}}.btn{animation:pulse 2s infinite;}</style>"""
    return css + f"""<div style="margin:50px 0;text-align:center;"><a href="{url}" class="btn" style="background:#b45309;color:white;padding:15px 30px;border-radius:50px;text-decoration:none;font-weight:bold;font-size:20px;">🔥 查看 {keyword} 最新優惠</a></div>"""

def get_hero_image(keyword):
    try:
        encoded = urllib.parse.quote(f"{keyword}, {IMG_STYLE}")
        seed = random.randint(1, 9999)
        url = f"https://image.pollinations.ai/prompt/{encoded}?seed={seed}&width=800&height=450&nologo=true"
        return f'<div style="text-align:center;margin-bottom:30px;"><img src="{url}" style="width:100%;border-radius:10px;"></div>'
    except: return ""

def generate_with_adaptive_retry(prompt):
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
    
    # 1. 取得真實存在的模型列表
    models_to_try = get_working_models()
    
    for model_name in models_to_try:
        # 如果模型名稱不包含 'gemini' 則跳過 (過濾掉其他實驗性模型)
        if 'gemini' not in model_name: continue

        logger.info(f"🚀 V51 嘗試模型: {model_name}")
        
        # 對每個模型嘗試生成 (含 429 重試邏輯)
        for attempt in range(3):
            try:
                # 這裡不需要 strip 'models/'，因為 API 接受完整路徑
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                
                if response and response.text:
                    logger.info("✅ 生成成功！")
                    return response
            
            except ResourceExhausted:
                wait_seconds = 70 
                logger.warning(f"⚠️ {model_name} 配額不足 (429)。等待 {wait_seconds} 秒...")
                time.sleep(wait_seconds)
                continue # 同一個模型再試一次
            
            except Exception as e:
                # 404 不會發生在這裡，因為我們是用 list_models 抓出來的
                # 但如果是其他 500 錯誤，就換下一個模型
                logger.error(f"❌ {model_name} 執行錯誤: {e} -> 切換下一個模型")
                break # 跳出 attempt 迴圈，進入下一個 model_name
                
    return None

def main():
    logger.info("====================================")
    logger.info("🏛️ V51 ARCHITECT EDITION STARTED 🏛️")
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
        
        【極重要格式指令 - 嚴格執行】：
        1. **直接輸出 HTML 代碼** (不要 Markdown，不要 ```html 包裹)。
        2. 使用 <h2> 標籤作為副標題。
        3. 使用 <p> 標籤包裹內文段落。
        4. 必須包含一個 HTML <table> 表格。
        5. 圖片位置請插入純文字標記: ((IMG: English Description))
        """
        
        res = generate_with_adaptive_retry(prompt)
        
        if res:
            # 清理可能殘留的 markdown
            html = res.text.replace("```html", "").replace("```", "")
            
            # 圖片處理
            def replacer(m): 
                return f'<img src="https://image.pollinations.ai/prompt/{urllib.parse.quote(m.group(1))}?nologo=true" style="width:100%;border-radius:10px;margin:20px 0;">'
            html = re.sub(r'\(\(IMG:(.*?)\)\)', replacer, html)
            
            # 暴力 CSS 注入 (確保排版完美)
            html = html.replace("<p>", '<p style="margin-bottom:25px;line-height:2.0;font-size:18px;color:#333;">')
            html = html.replace("<h2>", '<h2 style="color:#b45309;margin-top:40px;font-size:24px;border-bottom:2px solid #fbbf24;padding-bottom:10px;font-weight:bold;">')
            if "<table>" in html:
                html = html.replace("<table>", '<div style="overflow-x:auto;"><table border="1" style="width:100%;border-collapse:collapse;margin:30px 0;border:2px solid #333;">')
                html = html.replace("</table>", '</table></div>')
                html = html.replace("td>", 'td style="padding:15px;border:1px solid #ccc;">')
                html = html.replace("th>", 'th style="background:#fffbeb;padding:15px;border:1px solid #333;font-weight:bold;">')

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
