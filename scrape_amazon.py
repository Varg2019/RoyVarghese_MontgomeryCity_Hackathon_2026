import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup


URL = "https://www.amazon.com/PlayStation%C2%AE5-console-slim-PlayStation-5/dp/B0CL61F39H/"


def text_or_none(node):
    return node.get_text(" ", strip=True) if node else None


headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}

html = requests.get(URL, headers=headers, timeout=30).text
soup = BeautifulSoup(html, "html.parser")

title = text_or_none(soup.select_one("#productTitle"))
reviews = text_or_none(soup.select_one("#acrCustomerReviewText"))
image = soup.select_one("#landingImage")

price_whole = text_or_none(soup.select_one(".a-price .a-price-whole"))
price_fraction = text_or_none(soup.select_one(".a-price .a-price-fraction"))
price = None
if price_whole:
    price = f"{price_whole}{price_fraction or ''}"

bullets = []
for item in soup.select("#feature-bullets .a-list-item"):
    text = text_or_none(item)
    if text:
        bullets.append(text)

data = {
    "url": URL,
    "title": title,
    "price": price,
    "reviews": reviews,
    "image": image.get("src") if image else None,
    "bullets": bullets,
}

Path("data.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(data, indent=2, ensure_ascii=False))