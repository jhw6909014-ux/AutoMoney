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

# --- V33 CONFIG ---
SHOPEE_ID = "16332290023"
BOT_PERSONA = "3C科技發燒友"
IMG_STYLE = "cyberpunk style, futuristic, product photography, dramatic lighting"
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
    <div style="margin:50px 0;text-align:center;">
        <a href="{url}" target="_blank" rel="nofollow" 
           style="background-color:#60a5fa;color:white;padding:16px 32px;border-radius:50px;text-decoration:none;font-weight:bold;font-size:18px;box-shadow:0 4px 15px rgba(96,165,250,0.5);transition:all 0.3s;">
           🛍️ 查看「{keyword}」限時優惠
        </a>
    </div>
    """

# --- V33 修復：更穩定的圖片注入邏輯 ---
def inject_images_into_content(text):
    """
    搜尋 ((IMG: ...)) 標籤並替換為圖片。加入 Try-Except 防止崩潰。
    """
    try:
        def replacer(match):
            try:
                # 取得括號內的描述文字
                img_prompt = match.group(1).strip()
                if not img_prompt: return "" # 空標籤則忽略
                
                # 結合全域風格
                full_prompt = f"{img_prompt}, {IMG_STYLE}"
                encoded = urllib.parse.quote(full_prompt)
                
                # 隨機種子
                seed = random.randint(1, 99999)
                img_url = f"https://image.pollinations.ai/prompt/{encoded}?seed={seed}&width=800&height=450&nologo=true"
                
                return f"""
                <div style="margin: 30px 0; text-align: center;">
                    <img src="{img_url}" alt="{img_prompt}" style="width: 100%; max-width: 800px; border-radius: 12px; box-shadow: 0 8px 20px rgba(0,0,0,0.15);">
                    <p style="font-size: 13px; color: #888; margin-top: 8px; font-style: italic;">(AI 示意圖：{img_prompt})</p>
                </div>
                """
            except Exception as e:
                logger.error(f"單張圖片生成錯誤: {e}")
                return "" # 若單張失敗，回傳空字串，不影響文章

        # 使用 DOTALL 讓 . 可以匹配換行符號
        # 匹配雙括號 ((IMG: ... ))
        pattern = r'\(\(IMG:(.*?)\)\)'
        new_text = re.sub(pattern, replacer, text, flags=re.DOTALL | re.IGNORECASE)
        return new_text
        
    except Exception as e:
        logger.error(f"❌ 圖片注入流程發生嚴重錯誤: {e}")
        return text # 若發生嚴重錯誤，回傳原始文字，確保文章能發布

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

    # --- V33 提示詞：改用 ((IMG:...)) 避免 Markdown 衝突 ---
    prompt = f"""
    你是一位【{BOT_PERSONA}】。
    文章主題：【{keyword}】。
    新聞標題：{title}
    新聞摘要：{summary}
    
    請撰寫一篇豐富的部落格文章。
    
    【圖片指令 (重要)】：
    請在文章的「開頭」、「中間段落」和「結尾前」，根據該段落內容，插入總共 2 到 3 個圖片指令。
    指令格式請使用雙括號： ((IMG: 圖片的具體英文描述))
    例如：
    - 開頭： ((IMG: Close up of {keyword}, cinematic lighting))
    - 中間： ((IMG: detailed tech specs chart or component of {keyword}))
    
    【內容要求】：
    1. 輸出純 HTML 標籤 (不要輸出 ```html)。
    2. 使用 <h2> 分段標題。
    3. 必須包含一個 <table> 比較表格。
    4. 語氣生動專業。
    """
    
    for attempt in range(3):
        try:
            res = model.generate_content(prompt)
            if res.text:
                # 1. 清理 Markdown
                raw_html = res.text.replace("```html", "").replace("```", "")
                
                # 2. 注入圖片 (V33 防呆版)
                logger.info("正在注入圖片...")
                rich_html = inject_images_into_content(raw_html)
                
                # 3. 加入按鈕
                btn = create_shopee_button(keyword)
                
                return rich_html + btn
        except Exception as e:
            logger.error(f"⚠️ 生成錯誤 (第{attempt+1}次): {e}")
            time.sleep(2)
    return None

def main():
    logger.info("V33 Stable Bot Started...")
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
        
        content = ai_writer(entry.title, getattr(entry, "summary", ""), target_keyword)
        
        if content:
            emojis = ["🔥", "⚡", "💡", "🚀", "📢"]
            emo = random.choice(emojis)
            email_title = f"{emo} 【{target_keyword}】{entry.title}"
            
            success = send_email_to_blogger(email_title, content)
            if success:
                with open("history.txt", "a") as f: f.write(f"{entry.link}\n")
                    
    except Exception as e:
        logger.error(f"Main Error: {e}")

if __name__ == "__main__":
    main()
