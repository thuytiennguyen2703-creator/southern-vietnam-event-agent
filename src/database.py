import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from src.config import DB_PATH

def get_connection():
    """Tạo kết nối đến CSDL SQLite và cấu hình trả về kiểu Row."""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Khởi tạo cấu trúc bảng events trong CSDL SQLite."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            link TEXT UNIQUE NOT NULL,
            province TEXT,
            event_date TEXT,
            raw_date TEXT,
            location TEXT,
            scale TEXT,
            priority TEXT,
            source_name TEXT,
            published TEXT,
            is_sent INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Bổ sung nâng cấp bảng cũ nếu thiếu cột published
    try:
        cursor.execute("ALTER TABLE events ADD COLUMN published TEXT")
    except sqlite3.OperationalError:
        pass

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_raw_date ON events(raw_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_province ON events(province)")
    conn.commit()
    conn.close()

def save_event(event: Dict) -> bool:
    """Lưu một sự kiện mới vào CSDL (Đã thêm cột published)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO events (title, link, province, event_date, raw_date, location, scale, priority, source_name, published)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.get("title", ""),
            event.get("link", ""),
            event.get("province", "Miền Nam"),
            event.get("event_date", "Sắp diễn ra"),
            event.get("raw_date", ""),
            event.get("location", "Đang cập nhật địa điểm"),
            event.get("scale", ""),
            event.get("priority", "TB"),
            event.get("source_name", "Nguồn"),
            event.get("published", "")
        ))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Lỗi trùng lặp URL (link) hoặc trùng UNIQUE constraint
        print(f"ℹ️ Bỏ qua do trùng lặp dữ liệu (Link/ID đã tồn tại): {event.get('link')}")
        return False
    except Exception as e:
        print(f"Lỗi khi lưu sự kiện vào CSDL: {e}")
        return False
    finally:
        conn.close()

def get_unsent_events() -> List[Dict]:
    """Lấy danh sách các sự kiện mới cào về chưa được gửi báo cáo."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE is_sent = 0 ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_upcoming_events(days: int = 7) -> List[Dict]:
    """Lấy danh sách các sự kiện thực sự diễn ra trong khoảng X ngày tới."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM events WHERE raw_date >= ? ORDER BY raw_date ASC, id DESC LIMIT 20
    """, (today_str,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_as_sent(event_id: int):
    """Đánh dấu sự kiện đã được gửi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE events SET is_sent = 1 WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()