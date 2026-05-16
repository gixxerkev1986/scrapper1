import json
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

BASE_URL = "https://shop.dejongmarinelife.nl"
SCRAPE_URL = "https://shop.dejongmarinelife.nl/cultured-corals?orderby=date"

DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "dejong_corals.json")


def scrape_dejong_corals():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }

    response = requests.get(SCRAPE_URL, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    products = []

    # WooCommerce product cards
    product_cards = soup.select("li.product")

    for card in product_cards:
        print(card.prettify())
        link_el = card.select_one("a.woocommerce-LoopProduct-link, a")
        img_el = card.select_one("img")
        price_el = card.select_one(".price")

        title = title_el.get_text(strip=True) if title_el else "Onbekend"
        link = link_el.get("href") if link_el else ""
        image = img_el.get("data-src") or img_el.get("src") if img_el else ""
        price = price_el.get_text(" ", strip=True) if price_el else ""

        if link and link.startswith("/"):
            link = BASE_URL + link

        if image and image.startswith("/"):
            image = BASE_URL + image

        products.append({
            "title": title,
            "link": link,
            "image": image,
            "price": price,
            "category": "Cultured Corals",
            "source": "DeJong Marine Life",
            "scraped_at": datetime.now().isoformat(timespec="seconds")
        })

    os.makedirs(DATA_DIR, exist_ok=True)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    return products


def load_saved_corals():
    if not os.path.exists(DATA_FILE):
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()

            if not content:
                return []

            return json.loads(content)

    except json.JSONDecodeError:
        return []


if __name__ == "__main__":
    corals = scrape_dejong_corals()
    print(f"{len(corals)} koralen gevonden.")
