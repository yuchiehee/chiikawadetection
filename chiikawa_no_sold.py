import requests
from bs4 import BeautifulSoup
import time

# Discord Webhook
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1362386245208248370/CyJEMouBH4FRzd_PkfkRCq9T6G0aw9Sgo-4l-Nbv0Er3VMRvmcD0oynPtzakXeEFQgY5"

# Shopify API 分頁基礎網址
BASE_API = "https://chiikawamarket.jp/products.json?page={}"

def get_all_product_infos():
    all_products = []
    page = 1
    while True:
        url = BASE_API.format(page)
        res = requests.get(url)
        if res.status_code != 200:
            break
        data = res.json()
        products = data.get("products", [])
        if not products:
            break
        for product in products:
            name = product.get("title", "未知商品")
            handle = product.get("handle")
            image_url = product.get("images", [{}])[0].get("src", "")
            product_id = product.get("variants", [{}])[0].get("id", "未知編號")
            if handle:
                product_url = f"https://chiikawamarket.jp/zh-hant/products/{handle}"
                all_products.append({
                    "name": name,
                    "url": product_url,
                    "image": image_url,
                    "id": product_id
                })
        page += 1
        time.sleep(0.5)
    return all_products

def is_product_offline(url):
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            return True
        soup = BeautifulSoup(res.text, 'html.parser')
        error_texts = ["該頁面不存在", "該產品不存在", "已售完或不存在"]
        page_text = soup.get_text()
        return any(text in page_text for text in error_texts)
    except Exception as e:
        print(f"⚠️ 無法檢查 {url}：{e}")
        return False

def send_to_discord(message):
    payload = {"content": message}
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

# 🚀 主程式流程
print("正在抓取所有商品...")
all_products = get_all_product_infos()
print(f"共取得 {len(all_products)} 件商品，開始偵測下架...")

offline_items = []

for product in all_products:
    if is_product_offline(product["url"]):
        offline_items.append(product)

if offline_items:
    message_lines = ["⚠️ 以下商品被下架啦！"]
    for item in offline_items:
        message_lines.append(
            f"\n🧸 **{item['name']}**\n"
            f"📷 {item['image']}\n"
            f"🔗 {item['url']}\n"
            f"🆔 `{item['id']}`"
        )
    final_message = "\n".join(message_lines)
    send_to_discord(final_message)
    print(final_message)
else:
    send_to_discord("✅ 目前沒有商品被下架 嗚啦")
    print("✅ 沒有商品下架")
