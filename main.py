import os
import smtplib
import feedparser
import time
import google.generativeai as genai
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ================= 1. 讀取密碼 =================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
BLOGGER_EMAIL = os.environ.get("BLOGGER_EMAIL")

# ================= 2. 設定 AI (萬能鑰匙邏輯) =================
genai.configure(api_key=GOOGLE_API_KEY)

def get_ai_response(prompt):
    """
    自動嘗試多種模型，直到成功為止。
    這就像有三把鑰匙，第一把打不開就換第二把。
    """
    # 這是目前 Google 所有的免費模型清單，我們會一個一個試
    model_list = [
        "gemini-1.5-flash",          # 最新、最快 (首選)
        "gemini-1.5-flash-latest",   # 最新版的變體
        "gemini-1.0-pro",            # 舊版穩定款
        "gemini-pro"                 # 最舊版 (備用)
    ]

    for model_name in model_list:
        try:
            print(f"🔄 正在嘗試使用模型：{model_name} ...")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            # 確保有內容回傳
            if response.text:
                print(f"✅ 成功！由 {model_name} 完成寫作。")
                return response.text.replace("```html", "").replace("```", "").strip()
        except Exception as e:
            print(f"⚠️ {model_name} 失敗，嘗試下一個... (錯誤: {str(e)[:50]}...)")
            time.sleep(1) # 休息一下再試
            continue
    
    return None # 如果全部都失敗

RSS_URL = "https://www.theverge.com/rss/index.xml"

# ================= 3. 功能區 =================

def ai_write_article(title, summary, link):
    print(f"🤖 AI 正在準備撰寫：{title}...")
    
    prompt = f"""
    請將以下科技新聞改寫成一篇繁體中文部落格文章 (HTML 格式)。
    
    【標題】{title}
    【摘要】{summary}
    
    【要求】
    1. 標題使用 <h2> 標籤。
    2. 第一段後插入圖片：
       <br><div style="text-align:center;"><img src="https://image.pollinations.ai/prompt/{title.replace(' ', '%20')}?nologo=true" style="width:100%; max-width:600px; border-radius:10px;"></div><br>
    3. 加入優缺點分析。
    4. 文末加入按鈕：
       <br><div style="text-align:center; margin:30px 0;"><a href="{link}" style="background-color:#d93025; color:white; padding:15px 30px; text-decoration:none; border-radius:5px; font-weight:bold;">👉 點此閱讀完整報導</a></div>
    5. 只回傳 HTML 代碼。
    """
    
    return get_ai_response(prompt)

def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = BLOGGER_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ 信件已成功寄出！標題：{subject}")
    except Exception as e:
        print(f"❌ 寄信失敗 (請檢查 Gmail 密碼): {e}")

# ================= 4. 主程式 =================
if __name__ == "__main__":
    print(">>> 系統啟動 (萬能鑰匙版)...")
    
    if not GMAIL_APP_PASSWORD:
        print("❌ 錯誤：找不到環境變數")
        exit(1)

    try:
        feed = feedparser.parse(RSS_URL)
        if feed.entries:
            entry = feed.entries[0] # 抓最新一篇
            print(f"📄 發現新聞：{entry.title}")
            
            html_content = ai_write_article(entry.title, getattr(entry, 'summary', ''), entry.link)
            
            if html_content:
                send_email(entry.title, html_content)
            else:
                print("❌ 所有 AI 模型都嘗試失敗，請檢查 API Key 是否正確或額度是否用完。")
        else:
            print("📭 RSS 沒有新文章")
            
    except Exception as e:
        print(f"❌ 系統執行錯誤: {e}")
