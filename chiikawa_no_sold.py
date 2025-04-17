import requests
from bs4 import BeautifulSoup
import time

# Discord Webhook（請替換為你自己的）
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1362386245208248370/CyJEMouBH4FRzd_PkfkRCq9T6G0aw9Sgo-4l-Nbv0Er3VMRvmcD0oynPtzakXeEFQgY5"

# 每頁最多 50 筆，逐頁查詢
BASE_API = "https://chiikawamarket.jp/products.json?page={}"

def get_all_product_urls():
    all_products = {}
    page = 1
    while True:
        url = BASE_API.format(page)
        res = requests.get(url)
        if res.status_code != 200:
            break
        data = res.json()
        products = data.get("products", [])
        if not products:
            break  # 已無資料可抓
        for product in products:
            name = product.get("title", "未知商品")
            handle = product.get("handle")
            if handle:
                product_url = f"https://chiikawamarket.jp/zh-hant/products/{handle}"
                all_products[name] = product_url
        page += 1
        time.sleep(0.5)  # 避免對伺服器造成負擔
    return all_products

def is_product_offline(url):
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            return True
        soup = BeautifulSoup(res.text, 'html.parser')
        error_texts = ["該頁面不存在", "該產品不存在", "已售完或不存在"]
        page_text = soup.get_text()
        for text in error_texts:
            if text in page_text:
                return True
        return False
    except Exception as e:
        print(f"⚠️ 無法檢查 {url}：{e}")
        return False

def send_to_discord(message):
    payload = {"content": message}
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

# 🚀 主邏輯
print("正在抓取所有商品...")
all_products = get_all_product_urls()
print(f"共取得 {len(all_products)} 筆商品，開始偵測下架...")

for name, url in all_products.items():
    if is_product_offline(url):
        msg = f"⚠️【商品下架】「{name}」可能已經下架！\n🔗 {url}"
        send_to_discord(msg)
        print(msg)
    else:
        print(f"✅ {name} 正常在線")
