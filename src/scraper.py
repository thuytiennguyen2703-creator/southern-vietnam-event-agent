import html
import re
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}


def fetch_url(url: str) -> bytes:
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=20,
    )
    response.raise_for_status()
    return response.content


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)

    return " ".join(text.split())


def extract_article_content(url: str) -> str:
    if not url:
        return ""

    try:
        content = fetch_url(url)
    except requests.RequestException:
        return ""

    soup = BeautifulSoup(content, "html.parser")

    selectors = [
        "article",
        "[itemprop='articleBody']",
        ".article-content",
        ".article__body",
        ".detail-content",
        ".detail__content",
        ".content-detail",
        ".news-content",
        ".news-content-detail",
    ]

    for selector in selectors:
        element = soup.select_one(selector)

        if element:
            text = element.get_text(" ", strip=True)

            if len(text) >= 200:
                return clean_text(text)

    paragraphs = soup.find_all("p")

    text = " ".join(
        paragraph.get_text(" ", strip=True)
        for paragraph in paragraphs
    )

    return clean_text(text)


def scrape_rss_source(source: dict) -> list[dict]:
    content = fetch_url(source["url"])
    feed = feedparser.parse(content)

    articles = []

    for entry in feed.entries:
        title = clean_text(entry.get("title"))
        url = clean_text(entry.get("link"))
        summary = clean_text(entry.get("summary"))
        published = clean_text(entry.get("published"))

        if not title or not url:
            continue

        article_content = extract_article_content(url)

        articles.append({
            "source_name": source["name"],
            "source_url": source["url"],
            "province": source.get("province"),
            "title": title,
            "url": url,
            "summary": summary,
            "content": article_content,
            "published": published,
        })

    return articles


def scrape_html_source(source: dict) -> list[dict]:
    content = fetch_url(source["url"])
    soup = BeautifulSoup(content, "html.parser")

    articles = []
    seen_urls = set()

    for link in soup.find_all("a", href=True):
        title = clean_text(link.get_text(" ", strip=True))
        url = clean_text(link.get("href"))

        if not title or not url:
            continue

        url = urljoin(source["url"], url)

        if url in seen_urls:
            continue

        seen_urls.add(url)

        if url.startswith("#"):
            continue

        articles.append({
            "source_name": source["name"],
            "source_url": source["url"],
            "province": source.get("province"),
            "title": title,
            "url": url,
            "summary": "",
            "content": "",
            "published": "",
        })

    return articles


def scrape_source(source: dict) -> list[dict]:
    source_type = source.get("type")

    if source_type == "rss":
        return scrape_rss_source(source)

    if source_type == "html":
        return scrape_html_source(source)

    raise ValueError(
        f"Unsupported source type: {source_type}"
    )