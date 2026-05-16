import json
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

BASE_URL = "https://shop.dejongmarinelife.nl"
SCRAPE_URL = "https://shop.dejongmarinelife.nl/cultured-corals?orderby=date"

DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "dejong_corals.json")


def make_absolute_url(url):
    if not url:
        return ""

    if url.startswith("//"):
        return "https:" + url

    if url.startswith("/"):
        return BASE_URL + url

    return url


def get_title(card, link_el):
    selectors = [
        ".woocommerce-loop-product__title",
        ".product-title",
        ".title",
        "h2",
        "h3",
        "h4",
        "a[title]",
        "img[alt]",
    ]

    for selector in selectors:
        el = card.select_one(selector)

        if not el:
            continue

        if selector == "a[title]":
            title = el.get("title", "").strip()
        elif selector == "img[alt]":
            title = el.get("alt", "").strip()
        else:
            title = el.get_text(" ", strip=True)

        if title and title.lower() not in ["add to cart", "read more", "select options"]:
            return title

    if link_el:
        title = link_el.get("title", "").strip()
        if title:
            return title

    return "Onbekend"


def detect_category(title, link):
    text = f"{title} {link}".lower()

    if any(word in text for word in ["acropora", "montipora", "stylophora", "pocillopora", "seriatopora"]):
        return "SPS"

    if any(word in text for word in ["euphyllia", "hammer", "torch", "frogspawn", "goniopora", "alveopora", "acan", "favites", "lobophyllia", "trachyphyllia", "chalice"]):
        return "LPS"

    if any(word in text for word in ["zoanthus", "zoa", "mushroom", "ricordea", "discosoma", "rhodactis", "sinularia", "sarcophyton"]):
        return "Soft"

    return "Cultured Corals"


def scrape_dejong_corals():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    response = requests.get(SCRAPE_URL, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    products = []

    product_cards = soup.select("li.product")

    print(f"Productkaarten gevonden: {len(product_cards)}")

    for index, card in enumerate(product_cards, start=1):
        link_el = card.select_one("a.woocommerce-LoopProduct-link, a")
        img_el = card.select_one("img")
        price_el = card.select_one(".price, .woocommerce-Price-amount")

        title = get_title(card, link_el)

        link = link_el.get("href") if link_el else ""
        image = ""

        if img_el:
            image = (
                img_el.get("data-src")
                or img_el.get("data-lazy-src")
                or img_el.get("src")
                or ""
            )

        price = price_el.get_text(" ", strip=True) if price_el else ""

        link = make_absolute_url(link)
        image = make_absolute_url(image)

        category = detect_category(title, link)

        print(f"{index}. {title}")

        products.append({
            "title": title,
            "link": link,
            "image": image,
            "price": price,
            "category": category,
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
