import logging
import sqlite3
from typing import List, Dict

from src.config import DB_PATH
from src.database import init_db
from src.parser import process_articles
# Import hàm cào dữ liệu từ scraper.py của bạn
from src.scraper import fetch_all_sources

logger = logging.getLogger("pipeline")

def save_events_to_db(events: List[Dict]):
    """Lưu danh sách sự kiện đã bóc tách vào SQLite Database."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    saved_count = 0
    for e in events:
        try:
            cursor.execute(
                """
                INSERT OR IGNORE INTO events 
                (title, link, province, event_date, raw_date, location, scale, priority, source_name, published)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    e["title"], e["link"], e["province"], e["event_date"], 
                    e["raw_date"], e["location"], e["scale"], e["priority"], 
                    e["source_name"], e.get("published", "")
                )
            )
            if cursor.rowcount > 0:
                saved_count += 1
        except Exception as err:
            logger.error(f"Lỗi khi lưu sự kiện {e.get('title')}: {err}")

    conn.commit()
    conn.close()
    logger.info(f"✅ Đã lưu thành công {saved_count} sự kiện mới vào SQLite!")


def run_full_pipeline():
    """Hàm điều phối chính: Cào dữ liệu -> Xử lý AI/Parser -> Lưu CSDL."""
    logger.info("🚀 Bắt đầu chạy full pipeline cào dữ liệu...")
    try:
        # 1. Gọi scraper cào bài viết thô
        raw_arts = fetch_all_sources()
        logger.info(f"Thu thập được {len(raw_arts)} bài viết thô từ các nguồn.")
        
        # 2. Gọi parser xử lý dữ liệu
        events = process_articles(raw_arts)
        logger.info(f"Bóc tách thành công {len(events)} sự kiện Miền Nam hợp lệ.")
        
        # 3. Lưu vào Database
        if events:
            save_events_to_db(events)
        else:
            logger.info("Không có sự kiện mới nào được ghi nhận.")
    except Exception as e:
        logger.error(f"❌ Lỗi trong luồng pipeline: {e}", exc_info=True)