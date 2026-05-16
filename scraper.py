import json
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

BASE_URL = "https://shop.dejongmarinelife.nl"

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


def build_page_url(page):
    if page == 1:
        return f"{BASE_URL}/cultured-corals?orderby=date"

    return (
        f"{BASE_URL}/wysiwyg"
        f"?p={page}"
        f"&product_list_dir=desc"
        f"&product_list_order=created_at"
        f"&xhr=1"
    )


def get_title(card, link_el):
    selectors = [
        ".product-item-name a",
        ".product-item-link",
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

        if title and title.lower() not in [
            "add to cart",
            "read more",
            "select options"
        ]:
            return title

    if link_el:
        title = link_el.get("title", "").strip()

        if title:
            return title

    return "Onbekend"


def detect_category(title, link):
    text = f"{title} {link}".lower()

    if any(word in text for word in [
        "acropora",
        "montipora",
        "stylophora",
        "pocillopora",
        "seriatopora",
        "hydnophora",
        "birdsnest"
    ]):
        return "SPS"

    if any(word in text for word in [
        "euphyllia",
        "hammer",
        "torch",
        "frogspawn",
        "goniopora",
        "alveopora",
        "acan",
        "acanthastrea",
        "favites",
        "favia",
        "lobophyllia",
        "trachyphyllia",
        "chalice",
        "caulastrea",
        "duncan",
        "blastomussa",
        "micromussa",
        "cynarina",
        "scolymia"
    ]):
        return "LPS"

    if any(word in text for word in [
        "zoanthus",
        "zoa",
        "mushroom",
        "ricordea",
        "discosoma",
        "rhodactis",
        "sinularia",
        "sarcophyton",
        "clavularia",
        "xenia",
        "briareum",
        "pachyclavularia"
    ]):
        return "Soft"

    return "Cultured Corals"


def extract_html_from_response(response):
    html = response.text

    try:
        data = response.json()

        print("JSON TYPE:", type(data))

        if isinstance(data, dict):
            print("JSON KEYS:", data.keys())

            possible_keys = [
                "product_list_html",
                "products",
                "html",
                "content",
                "items",
                "product_list",
                "list",
                "output",
                "data"
            ]

            for key in possible_keys:
                if key in data and data[key]:
                    html = data[key]
                    print(f"HTML gevonden in key: {key}")
                    break

            if isinstance(html, list):
                html = "".join(str(item) for item in html)

            if isinstance(html, dict):
                html = json.dumps(html)

    except Exception as e:
        print("Geen JSON response:", e)

    return html


def scrape_page(page):
    url = build_page_url(page)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        ),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE_URL}/wysiwyg",
    }

    print(f"Scrapen pagina {page}: {url}")

    response = requests.get(url, headers=headers, timeout=20)

    if response.status_code == 404:
        print(f"Pagina {page} bestaat niet.")
        return []

    response.raise_for_status()

    html = extract_html_from_response(response)

    soup = BeautifulSoup(html, "lxml")

    product_cards = soup.select(
        "li.product-item, "
        ".product-item, "
        ".item.product, "
        ".products-grid .item, "
        ".product"
    )

    print(f"Productkaarten op pagina {page}: {len(product_cards)}")

    products = []

    for card in product_cards:
        link_el = card.select_one(
            "a.product-item-link, "
            "a.woocommerce-LoopProduct-link, "
            ".product-item-photo, "
            "a"
        )

        img_el = card.select_one("img")

        price_el = card.select_one(
            ".price, "
            ".woocommerce-Price-amount, "
            ".price-box"
        )

        title = get_title(card, link_el)

        link = link_el.get("href") if link_el else ""

        image = ""

        if img_el:
            image = (
                img_el.get("data-src")
                or img_el.get("data-lazy-src")
                or img_el.get("data-original")
                or img_el.get("data-srcset")
                or img_el.get("src")
                or ""
            )

            if "," in image:
                image = image.split(",")[0].strip().split(" ")[0]

        price = price_el.get_text(" ", strip=True) if price_el else ""

        link = make_absolute_url(link)
        image = make_absolute_url(image)

        category = detect_category(title, link)

        products.append({
            "title": title,
            "link": link,
            "image": image,
            "price": price,
            "category": category,
            "source": "DeJong Marine Life",
            "page": page,
            "scraped_at": datetime.now().isoformat(timespec="seconds")
        })

    return products


def remove_duplicates(products):
    unique = {}

    for product in products:
        key = product.get("link") or product.get("title")

        if key:
            unique[key] = product

    return list(unique.values())


def scrape_dejong_corals(max_pages=20):
    all_products = []

    for page in range(1, max_pages + 1):
        page_products = scrape_page(page)

        if not page_products:
            print(f"Geen producten meer gevonden op pagina {page}. Stoppen.")
            break

        all_products.extend(page_products)

    all_products = remove_duplicates(all_products)

    os.makedirs(DATA_DIR, exist_ok=True)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_products, f, ensure_ascii=False, indent=2)

    print(f"Totaal unieke koralen gevonden: {len(all_products)}")

    return all_products


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
