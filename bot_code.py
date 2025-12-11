import os
import time
import random
import logging
import urllib.parse
import feedparser
import google.generativeai as genai
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods import posts

# --- V28 CONFIG (內建黃金字庫) ---
SHOPEE_ID = "16332290023"
WP_CATEGORY = "Uncategorized"
BOT_PERSONA = "3C科技發燒友，語氣專業且熱愛新知"

# 這是由產生器寫死的字庫，確保關鍵字精準
KEYWORD_POOL = ["iPhone","Android","顯示卡","人工智慧","筆電","藍芽耳機","Switch","PS5","智慧手錶","Nvidia"]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def get_dynamic_rss():
    """
    V28 核心：每次執行時，從字庫中隨機挑選一個關鍵字。
    好處：內容多元，且能針對不同產品生成精準的蝦皮連結。
    """
    target_keyword = random.choice(KEYWORD_POOL)
    logger.info(f"🎯 本次鎖定黃金關鍵字: {target_keyword}")
    
    # 轉換為 Google News RSS 連結
    encoded = urllib.parse.quote(target_keyword)
    rss_url = f"https://news.google.com/rss/search?q={encoded}+when:1d&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    
    return rss_url, target_keyword

def create_shopee_button(keyword):
    # 使用當次隨機選中的「黃金關鍵字」來搜尋，保證商品相關性極高
    safe_keyword = urllib.parse.quote(keyword)
    url = f"https://shopee.tw/search?keyword={safe_keyword}&utm_source=affiliate&utm_campaign={SHOPEE_ID}"
    
    return f"""
    <div style="margin:40px 0;text-align:center;">
        <p style="font-size:15px;color:#666;margin-bottom:10px;">👇 {keyword} 相關優惠與推薦 👇</p>
        <a href="{url}" target="_blank" rel="nofollow" 
           style="background-color:#ee4d2d;color:white;padding:15px 30px;border-radius:50px;text-decoration:none;font-weight:bold;font-size:18px;box-shadow:0 4px 10px rgba(238,77,45,0.4);">
           🔍 點此在蝦皮搜尋「{keyword}」
        </a>
    </div>
    """

def ai_writer(title, summary, keyword):
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key: return None
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    你是一位【{BOT_PERSONA}】。
    本次主題關鍵字是：【{keyword}】。
    
    請將以下新聞改寫成一篇繁體中文部落格文章。
    新聞標題: {title}
    新聞摘要: {summary}
    
    【寫作指令】:
    1. 標題：必須包含「{keyword}」，並且要是吸引人的農場標題。
    2. 內容：請自然地將 {keyword} 融入文章中，強調其重要性或選購要點。
    3. 表格：請製作一個 HTML 表格 (<table>)，列出關於 {keyword} 的相關規格比較、選購指南或優缺點分析。
    4. 結尾：給出針對 {keyword} 的具體購買建議。
    """
    
    for _ in range(3):
        try:
            res = model.generate_content(prompt)
            if res.text:
                text = res.text.replace("```html", "").replace("```", "")
                # 植入精準按鈕
                btn = create_shopee_button(keyword)
                return text + btn
        except:
            time.sleep(2)
    return None

def main():
    logger.info("V28 Auto-Hunter Started...")
    wp_url = os.environ.get("WORDPRESS_URL")
    wp_user = os.environ.get("WORDPRESS_USER")
    wp_pass = os.environ.get("WORDPRESS_APP_PASSWORD")
    
    if not wp_url: return

    # 1. 獲取隨機 RSS 和 關鍵字
    rss_url, target_keyword = get_dynamic_rss()
    
    feed = feedparser.parse(rss_url)
    history = []
    if os.path.exists("history.txt"):
        with open("history.txt", "r") as f: history = f.read().splitlines()
        
    # 每次只處理 1 篇，避免洗版，且確保每篇主題不同
    for entry in feed.entries[:1]:
        if entry.link in history: continue
        
        logger.info(f"Writing Article: {entry.title}")
        
        # 傳入 target_keyword 讓 AI 針對該產品寫作
        content = ai_writer(entry.title, getattr(entry, "summary", ""), target_keyword)
        
        if content:
            try:
                client = Client(wp_url, wp_user, wp_pass)
                post = WordPressPost()
                post.title = f"【{target_keyword}快訊】{entry.title}"
                post.content = content
                post.post_status = 'publish'
                post.terms_names = {'category': [WP_CATEGORY]}
                
                client.call(posts.NewPost(post))
                
                with open("history.txt", "a") as f: f.write(f"{entry.link}\n")
                logger.info("Published Successfully!")
            except Exception as e:
                logger.error(f"WP Error: {e}")

if __name__ == "__main__":
    main()
