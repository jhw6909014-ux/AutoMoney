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

# --- V32 CONFIG ---
SHOPEE_ID = "16332290023"
BOT_PERSONA = "3C科技發燒友"
IMG_STYLE = "cyberpunk style, futuristic, product photography, dramatic lighting, high tech"
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
           style="background-color:#e94560;color:white;padding:16px 32px;border-radius:50px;text-decoration:none;font-weight:bold;font-size:18px;box-shadow:0 4px 15px rgba(233,69,96,0.5);transition:all 0.3s;">
           🛍️ 查看「{keyword}」限時優惠
        </a>
    </div>
    """

# --- V32 核心：動態圖片注入 ---
def inject_images_into_content(text):
    """
    搜尋文字中的 [IMG: ...] 標籤，並將其替換為 Pollinations 的圖片連結
    """
    def replacer(match):
        # 取得 [] 裡面的描述文字
        img_prompt = match.group(1)
        
        # 結合全域風格設定
        full_prompt = f"{img_prompt}, {IMG_STYLE}"
        encoded = urllib.parse.quote(full_prompt)
        
        # 隨機種子確保圖片不重複
        seed = random.randint(1, 99999)
        img_url = f"https://image.pollinations.ai/prompt/{encoded}?seed={seed}&width=800&height=450&nologo=true"
        
        # 回傳美化的 img 標籤
        return f"""
        <div style="margin: 30px 0; text-align: center;">
            <img src="{img_url}" alt="{img_prompt}" style="width: 100%; max-width: 800px; border-radius: 12px; box-shadow: 0 8px 20px rgba(0,0,0,0.15);">
            <p style="font-size: 13px; color: #666; margin-top: 8px; font-style: italic;">(AI 示意圖：{img_prompt})</p>
        </div>
        """

    # 使用 Regex 替換所有 [IMG: ...]
    # Pattern 說明: [IMG: 抓取開頭, (.*?) 抓取內容, ] 抓取結尾
    new_text = re.sub(r'[IMG:s*(.*?)]', replacer, text)
    return new_text

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

    # --- V32 關鍵：指示 AI 在文中插入圖片標籤 ---
    prompt = f"""
    你是一位【{BOT_PERSONA}】。
    文章主題：【{keyword}】。
    新聞標題：{title}
    新聞摘要：{summary}
    
    請撰寫一篇豐富的部落格文章。
    
    【圖片指令 (非常重要)】：
    請在文章的「開頭」、「中間段落」和「結尾前」，根據該段落的內容，插入總共 2 到 3 個圖片佔位符。
    格式必須是： [IMG: 圖片的具體英文描述]
    例如：
    - 開頭放： [IMG: Close up of {keyword}, cinematic lighting]
    - 講到規格時放： [IMG: detailed tech specs chart or component of {keyword}]
    
    【HTML 格式要求】：
    1. 不要輸出 ```html 標記。
    2. 使用 <h2> 分段標題。
    3. 必須包含一個 HTML <table> 比較表格。
    4. 內容要豐富，語氣生動。
    """
    
    for attempt in range(3):
        try:
            res = model.generate_content(prompt)
            if res.text:
                # 1. 清理 Markdown
                raw_html = res.text.replace("```html", "").replace("```", "")
                
                # 2. 注入圖片 (V32 新功能)
                rich_html = inject_images_into_content(raw_html)
                
                # 3. 加入按鈕
                btn = create_shopee_button(keyword)
                
                return rich_html + btn
        except Exception as e:
            logger.error(f"⚠️ 錯誤: {e}")
            time.sleep(2)
    return None

def main():
    logger.info("V32 Ultimate Bot Started...")
    rss_url, target_keyword = get_dynamic_rss()
    
    try:
        feed = feedparser.parse(rss_url)
        if not feed.entries: return
            
        history = []
        if os.path.exists("history.txt"):
            with open("history.txt", "r") as f: history = f.read().splitlines()
        
        # 篩選新文章
        candidates = [e for e in feed.entries if e.link not in history]
        if not candidates: return

        # 隨機選一篇
        entry = random.choice(candidates[:3])
        logger.info(f"Processing: {entry.title}")
        
        content = ai_writer(entry.title, getattr(entry, "summary", ""), target_keyword)
        
        if content:
            # 標題加入吸睛 Emoji
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
