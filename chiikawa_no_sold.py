import requests
from bs4 import BeautifulSoup
import time
import json
from pathlib import Path
import subprocess

# Discord Webhook
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1362386245208248370/CyJEMouBH4FRzd_PkfkRCq9T6G0aw9Sgo-4l-Nbv0Er3VMRvmcD0oynPtzakXeEFQgY5"

# Shopify API 分頁基礎網址
BASE_API = "https://chiikawamarket.jp/products.json?page={}"

# 商品清單儲存路徑（第一次跑會自動建立）
JSON_PATH = "products_latest.json"

# 抓取目前全商品清單
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
            
            images = product.get("images", [])
            image_url = images[0].get("src", "") if images else ""
            
            variant = product.get("variants", [{}])[0]
            product_id = str(variant.get("id", "未知編號"))
            product_sku = variant.get("sku", "（無 SKU）")

            if handle:
                product_url = f"https://chiikawamarket.jp/zh-hant/products/{handle}"
                all_products.append({
                    "name": name,
                    "url": product_url,
                    "image": image_url,
                    "id": product_id,
                    "sku": product_sku
                })
        page += 1
        time.sleep(0.5)
    return all_products

# 載入前次清單
def load_previous_list(path):
    if Path(path).exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# 儲存目前清單
def save_current_list(products, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

# 發送 Discord 訊息
def send_to_discord(message):
    payload = {"content": message}
    res = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if res.status_code == 204:
        print("✅ 成功發送到 Discord")
    else:
        print(f"⚠️ 發送失敗！Status code: {res.status_code}")
        print(res.text)

# 比對上下架
def compare_product_lists(old_list, new_list):
    old_ids = {p["id"]: p for p in old_list}
    new_ids = {p["id"]: p for p in new_list}

    new_items = [new_ids[i] for i in new_ids if i not in old_ids]
    removed_items = [old_ids[i] for i in old_ids if i not in new_ids]
    return new_items, removed_items

# 將最新商品清單加入 Git commit
def commit_json_to_repo():
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=True)
        subprocess.run(["git", "add", JSON_PATH], check=True)
        result = subprocess.run(["git", "commit", "-m", "Update latest product list"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ 商品清單已更新並提交")
            subprocess.run(["git", "push"], check=True)
        else:
            print("ℹ️ 無需更新商品清單（無內容變動）")
    except Exception as e:
        print(f"❌ Git 操作失敗：{e}")


# 防止超過dc字數上限
def send_long_message(message, chunk_size=1900):
    # Discord 限制 content 最多 2000 字元，留點 buffer
    for i in range(0, len(message), chunk_size):
        chunk = message[i:i + chunk_size]
        payload = {"content": chunk}
        res = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if res.status_code == 204:
            print("✅ 成功發送一段訊息")
        else:
            print(f"⚠️ 發送失敗 {res.status_code}：{res.text}")

# 傳送embeds
def send_embeds(products, status="new"):
    status_emoji = "🆕" if status == "new" else "⚠️"
    color = 0x2ecc71 if status == "new" else 0xe74c3c  # 綠 / 紅

    for i in range(0, len(products), 10):  # Discord embeds 一次最多 10 個
        embeds = []
        for p in products[i:i+10]:
            embed = {
                "title": f"{status_emoji} {p['name']}",
                "url": p["url"],
                "color": color,
                "fields": [
                    {
                        "name": "商品編號",
                        "value": f"{p.get('sku', '無')}",
                        "inline": False
                    }
                ],
                "image": {
                    "url": p["image"]
                }
            }
            embeds.append(embed)

        payload = {"embeds": embeds}
        res = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if res.status_code == 204:
            print(f"✅ 發送 {status} embeds 成功")
        else:
            print(f"⚠️ 發送 {status} embeds 失敗：{res.status_code} - {res.text}")


# 🚀 主流程
# send_to_discord("🤖 Chiikawa 商品偵測器啟動囉！")

print("🚀 抓取目前商品清單...")
new_products = get_all_product_infos()
old_products = load_previous_list(JSON_PATH)

print(f"📊 目前商品數量: {len(new_products)}，開始比對上下架...")
new_items, removed_items = compare_product_lists(old_products, new_products)

if new_items:
    send_to_discord("🆕 **新上架商品** 🆕")
    send_embeds(new_items, status="new")

if removed_items:
    send_to_discord("⚠️ **以下商品被下架** ⚠️")
    send_embeds(removed_items, status="removed")

if not new_items and not removed_items:
    send_to_discord("✅ 目前商品無變動，嗚啦 ✅")

# 儲存目前清單供下次比較
save_current_list(new_products, JSON_PATH)
commit_json_to_repo()
