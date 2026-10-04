import logging
import urllib.request
import feedparser
import requests
from typing import List, Dict
from src.config import RSS_SOURCES
from src.bot_handler import send_telegram_message

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def fetch_single_source(source: Dict) -> tuple[List[Dict], str | None]:
    """Thu thập bài viết từ một nguồn RSS với cơ chế dự phòng hai lớp (requests + urllib)"""
    articles = []
    source_name = source["name"]
    url = source["url"]

    content = None
    error_msg = None

    # Lớp 1: Dùng requests
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code == 200:
            content = response.content
        else:
            error_msg = f"Mã lỗi HTTP {response.status_code}"
    except Exception as e:
        # Lớp 2: Dự phòng dùng urllib nếu gặp lỗi HeaderParsingError trên Python 3.14
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read()
        except Exception as ex:
            error_msg = f"Lỗi kết nối: {str(ex)}"

    if error_msg or not content:
        return [], error_msg or "Không tải được nội dung"

    feed = feedparser.parse(content)

    for entry in feed.entries:
        title = getattr(entry, "title", "")
        link = getattr(entry, "link", "")
        summary = getattr(entry, "summary", getattr(entry, "description", ""))
        published = getattr(entry, "published", getattr(entry, "updated", ""))

        if title and link:
            articles.append({
                "title": title.strip(),
                "link": link.strip(),
                "summary": summary,
                "published": published,
                "source_name": source_name
            })

    return articles, None


def fetch_all_sources() -> List[Dict]:
    """Thu thập dữ liệu từ tất cả các nguồn và tự động phát cảnh báo nếu nguồn hỏng"""
    all_articles = []
    failed_sources = []

    for source in RSS_SOURCES:
        logging.info(f"Đang cào dữ liệu từ: {source['name']}")
        articles, error = fetch_single_source(source)

        if error:
            logging.error(f"❌ Nguồn '{source['name']}' bị hỏng: {error}")
            failed_sources.append({"name": source["name"], "url": source["url"], "error": error})
        else:
            all_articles.extend(articles)

    # Tự động gửi cảnh báo về Telegram nếu có nguồn hỏng
    if failed_sources:
        alert_text = "⚠️ <b>CẢNH BÁO: PHÁT HIỆN NGUỒN THU THẬP BỊ HỎNG!</b> ⚠️\n\n"
        for fs in failed_sources:
            alert_text += f"❌ <b>Nguồn:</b> {fs['name']}\n"
            alert_text += f"🔗 <b>URL:</b> {fs['url']}\n"
            alert_text += f"🛠️ <b>Chi tiết lỗi:</b> <code>{fs['error']}</code>\n"
            alert_text += "───────────────────\n"
        
        send_telegram_message(alert_text)

    return all_articles