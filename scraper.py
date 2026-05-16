import json
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

BASE_URL = "https://shop.dejongmarinelife.nl"

DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "dejong_corals.json")

SCRAPE_SOURCES = {
    "wysiwyg": {
        "name": "WYSIWYG",
        "url": "https://shop.dejongmarinelife.nl/wysiwyg",
        "mode": "xhr"
    },
    "cultured": {
        "name": "Cultured Corals",
        "url": "https://shop.dejongmarinelife.nl/cultured-corals",
        "mode": "hybrid"
    },
    "custom": {
        "name": "Custom URL",
        "url": "",
        "mode": "auto"
    }
}


def make_absolute_url(url):
    if not url:
        return ""

    if url.startswith("//"):
        return "https:" + url

    if url.startswith("/"):
        return BASE_URL + url

    return url


def clean_source_url(url):
    if not url:
        return ""

    url = url.strip()

    if url.startswith("/"):
        url = BASE_URL + url

    return url


def build_page_url(source_url, page, mode="auto"):
    source_url = clean_source_url(source_url)

    parsed = urlparse(source_url)
    query = parse_qs(parsed.query)

    if mode in ["xhr", "auto"]:
        query["p"] = [str(page)]
        query["product_list_dir"] = ["desc"]
        query["product_list_order"] = ["created_at"]
        query["xhr"] = ["1"]

        new_query = urlencode(query, doseq=True)

        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))

    if mode == "normal":
        if page == 1:
            return source_url

        path = parsed.path.rstrip("/") + f"/page/{page}/"
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))

    if mode == "hybrid":
        if page == 1:
            query["orderby"] = ["date"]
            new_query = urlencode(query, doseq=True)

            return urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment
            ))

        xhr_url = f"{BASE_URL}/wysiwyg"
        return build_page_url(xhr_url, page, mode="xhr")

    return source_url


def get_title(card, link_el):
    selectors = [
        ".product-item-name a",
        ".product-item-link",
        ".woocommerce-loop-product__title",
        ".product-title",
        ".grouped-product-name",
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
        "acropora", "montipora", "stylophora", "pocillopora",
        "seriatopora", "hydnophora", "birdsnest"
    ]):
        return "SPS"

    if any(word in text for word in [
        "euphyllia", "hammer", "torch", "frogspawn", "goniopora",
        "alveopora", "acan", "acanthastrea", "favites", "favia",
        "lobophyllia", "trachyphyllia", "chalice", "caulastrea",
        "duncan", "blastomussa", "micromussa", "cynarina", "scolymia"
    ]):
        return "LPS"

    if any(word in text for word in [
        "zoanthus", "zoa", "mushroom", "ricordea", "discosoma",
        "rhodactis", "sinularia", "sarcophyton", "clavularia",
        "xenia", "briareum", "pachyclavularia"
    ]):
        return "Soft"

    return "Cultured Corals"


def detect_stock_status(card):
    check_blocks = [card]

    parent = card.parent
    for _ in range(5):
        if parent:
            check_blocks.append(parent)
            parent = parent.parent

    for block in check_blocks:
        stock_el = block.select_one(".stock")

        if not stock_el:
            continue

        stock_classes = " ".join(stock_el.get("class", [])).lower()
        stock_text = stock_el.get_text(" ", strip=True).lower()

        if (
            "unavailable" in stock_classes
            or "out-of-stock" in stock_classes
            or "out_of_stock" in stock_classes
            or "out of stock" in stock_text
            or "sold out" in stock_text
            or "unavailable" in stock_text
        ):
            return "out_of_stock"

        return "in_stock"

    full_text = card.get_text(" ", strip=True).lower()
    full_html = str(card).lower()

    if (
        "out of stock" in full_text
        or "sold out" in full_text
        or "stock unavailable" in full_html
        or 'class="stock unavailable"' in full_html
        or "class='stock unavailable'" in full_html
    ):
        return "out_of_stock"

    return "unknown"


def extract_html_from_response(response):
    html = response.text

    try:
        data = response.json()

        if isinstance(data, dict):
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
                    break

            if isinstance(html, list):
                html = "".join(str(item) for item in html)

            if isinstance(html, dict):
                html = json.dumps(html)

    except Exception:
        pass

    return html


def scrape_page(source_url, page, mode="auto", source_name="DeJong"):
    url = build_page_url(source_url, page, mode)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        ),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": source_url,
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
            ".price-box, "
            ".js-price-per-piece"
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
        stock_status = detect_stock_status(card)

        if (
            title != "Onbekend"
            and image
            and stock_status == "in_stock"
        ):
            products.append({
                "title": title,
                "link": link,
                "image": image,
                "price": price,
                "category": category,
                "stock_status": stock_status,
                "source": source_name,
                "source_url": source_url,
                "page": page,
                "scraped_at": datetime.now().isoformat(timespec="seconds")
            })

    return products


def remove_duplicates(products):
    unique = {}

    for product in products:
        title = product.get("title", "").strip().lower()
        image = product.get("image", "").strip()

        if not title or not image:
            continue

        key = f"{title}|{image}"

        if key not in unique:
            unique[key] = product
        else:
            existing = unique[key]

            if not existing.get("link") and product.get("link"):
                existing["link"] = product.get("link")

            if not existing.get("price") and product.get("price"):
                existing["price"] = product.get("price")

    return list(unique.values())


def get_source_config(source_key="wysiwyg", custom_url=None):
    source = SCRAPE_SOURCES.get(source_key, SCRAPE_SOURCES["wysiwyg"]).copy()

    if source_key == "custom" and custom_url:
        source["url"] = clean_source_url(custom_url)
        source["mode"] = "auto"
        source["name"] = "Custom URL"

    return source


def scrape_dejong_corals(source_key="wysiwyg", custom_url=None, max_pages=20):
    source = get_source_config(source_key, custom_url)

    source_url = source["url"]
    mode = source["mode"]
    source_name = source["name"]

    if not source_url:
        raise ValueError("Geen geldige URL opgegeven.")

    all_products = []

    print(f"Bron: {source_name}")
    print(f"URL: {source_url}")
    print(f"Mode: {mode}")

    for page in range(1, max_pages + 1):
        page_products = scrape_page(
            source_url=source_url,
            page=page,
            mode=mode,
            source_name=source_name
        )

        if not page_products:
            print(f"Geen beschikbare producten meer gevonden op pagina {page}. Stoppen.")
            break

        all_products.extend(page_products)

    all_products = remove_duplicates(all_products)

    os.makedirs(DATA_DIR, exist_ok=True)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_products, f, ensure_ascii=False, indent=2)

    print(f"Totaal unieke beschikbare koralen gevonden: {len(all_products)}")

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
    corals = scrape_dejong_corals(source_key="wysiwyg")
    print(f"{len(corals)} beschikbare koralen gevonden.")
