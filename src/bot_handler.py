import html
import logging
import os
import re
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List

import pandas as pd
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from src.config import DB_PATH, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from src.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(name)s] %(message)s",
)
logger = logging.getLogger("bot_handler")

import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Handler phản hồi 200 OK cho Render health check
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")
        
    def log_message(self, format, *args):
        # Tắt log HTTP rác để bớt tràn terminal
        return

def start_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()


def clean_text(text: str) -> str:
    """Giải mã HTML Entities và loại bỏ triệt để các thẻ HTML rác gây lỗi Telegram API."""
    if not text:
        return ""
    decoded = html.unescape(html.unescape(text))
    clean = re.sub(r"</?[a-zA-Z0-9\-_:]+[^>]*>", "", decoded)
    return clean.strip()


def format_daily_report(
    events: List[Dict], title_prefix: str = "BẢN TIN SỰ KIỆN MIỀN NAM"
) -> str:
    """Định dạng bản tin sự kiện chuẩn 100% theo mẫu thiết kế."""
    if not events:
        return f"<b>{title_prefix}</b>\n\nKhông có sự kiện nào được ghi nhận trong thời gian này."

    now = datetime.now()
    days_vn = [
        "Thứ Hai",
        "Thứ Ba",
        "Thứ Tư",
        "Thứ Năm",
        "Thứ Sáu",
        "Thứ Bảy",
        "Chủ Nhật",
    ]
    day_name = days_vn[now.weekday()]
    date_str = now.strftime("%d/%m/%Y")

    high_priority_count = sum(1 for e in events if e.get("priority") == "CAO")

    msg = f"<b>{title_prefix} — 07:00 {day_name} {date_str}</b>\n\n"
    msg += f"<b>Tổng số: {len(events)} sự kiện ({high_priority_count} quy mô lớn)</b>\n\n"

    for e in events:
        priority = e.get("priority", "TB")
        province = html.escape(clean_text(e.get("province", "Miền Nam")))
        event_date = html.escape(clean_text(e.get("event_date", "Sắp diễn ra")))
        title = html.escape(clean_text(e.get("title", "")))
        location = html.escape(
            clean_text(e.get("location", "Đang cập nhật địa điểm"))
        )
        scale = html.escape(clean_text(e.get("scale", "")))
        source_name = html.escape(clean_text(e.get("source_name", "Nguồn")))
        link = e.get("link", "")

        msg += f"<b>[{priority}] {event_date} · {province}</b>\n\n"
        msg += f"<b>{title}</b>\n\n"
        msg += f"Địa điểm: {location}\n\n"

        if scale:
            msg += f"Quy mô: {scale}\n\n"

        if link:
            msg += f'Nguồn: <a href="{link}">{source_name}</a>\n\n'
        else:
            msg += f"Nguồn: {source_name}\n\n"

        msg += "───────────────────\n\n"

    msg += (
        "Gõ /tuannay để xem đầy đủ, /tinh &lt;tên tỉnh&gt;, /sukien &lt;từ"
        " khóa&gt;, hoặc /excel để tải báo cáo."
    )
    return msg


def send_telegram_message(text: str, max_length: int = 3500) -> bool:
    """Gửi thông báo chủ động qua Telegram API (cho Scheduler/Main pipeline)."""
    token = str(TELEGRAM_BOT_TOKEN).strip() if TELEGRAM_BOT_TOKEN else ""
    chat_id = str(TELEGRAM_CHAT_ID).strip() if TELEGRAM_CHAT_ID else ""

    if not token or not chat_id:
        logger.error("Chưa cấu hình TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID trong .env")
        return False

    if token.startswith("bot"):
        token = token[3:]

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    blocks = text.split("───────────────────\n\n")
    chunks = []
    current_chunk = ""

    for block in blocks:
        if len(current_chunk) + len(block) + 25 > max_length:
            chunks.append(current_chunk)
            current_chunk = block + "───────────────────\n\n"
        else:
            current_chunk += block + "───────────────────\n\n"

    if current_chunk:
        chunks.append(current_chunk)

    all_success = True
    for chunk in chunks:
        if not chunk.strip():
            continue

        payload = {
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            res_data = response.json()
            if not res_data.get("ok"):
                logger.error(f"Lỗi Telegram API: {res_data.get('description')}")
                all_success = False
        except Exception as e:
            logger.error(f"Lỗi gửi tin Telegram: {e}")
            all_success = False

    return all_success


async def send_split_messages(update: Update, text: str, max_length: int = 3500):
    """Phản hồi tin nhắn tương tác người dùng cho các Bot Commands."""
    if len(text) <= max_length:
        await update.message.reply_text(
            text, parse_mode="HTML", disable_web_page_preview=True
        )
        return

    blocks = text.split("───────────────────\n\n")
    chunks = []
    current_chunk = ""

    for block in blocks:
        if len(current_chunk) + len(block) + 25 > max_length:
            chunks.append(current_chunk)
            current_chunk = block + "───────────────────\n\n"
        else:
            current_chunk += block + "───────────────────\n\n"

    if current_chunk:
        chunks.append(current_chunk)

    for chunk in chunks:
        if chunk.strip():
            await update.message.reply_text(
                chunk, parse_mode="HTML", disable_web_page_preview=True
            )


# ==========================================
# CÁC LỆNH TƯƠNG TÁC TELEGRAM (BOT COMMANDS)
# ==========================================


async def cmd_homnay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /homnay: Lọc sự kiện diễn ra đúng ngày hôm nay."""
    init_db()
    today_str = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM events WHERE raw_date = ? ORDER BY id DESC LIMIT 10",
        (today_str,),
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text(
            "<b>BẢN TIN SỰ KIỆN HÔM NAY</b>\n\nHôm nay không có sự kiện nào diễn ra.\nGõ /tuannay để xem danh sách 7 ngày tới.",
            parse_mode="HTML",
        )
        return

    events = [dict(r) for r in rows]
    report = format_daily_report(events, title_prefix="BẢN TIN SỰ KIỆN HÔM NAY")
    await send_split_messages(update, report)


async def cmd_tuannay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /tuannay: Chỉ lọc các sự kiện thực sự diễn ra trong khoảng 7 ngày tới."""
    init_db()
    today_str = datetime.now().strftime("%Y-%m-%d")
    next_7_days = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Chỉ lấy sự kiện có ngày diễn ra từ HÔM NAY đến 7 NGÀY TỚI (loại bỏ tin 'Sắp diễn ra')
    cursor.execute(
        "SELECT * FROM events WHERE raw_date >= ? AND raw_date <= ? ORDER BY raw_date ASC, id DESC LIMIT 15",
        (today_str, next_7_days),
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text(
            "<b>BẢN TIN SỰ KIỆN 7 NGÀY TỚI</b>\n\nHiện tại không có sự kiện nào diễn ra trong 7 ngày tới.",
            parse_mode="HTML",
        )
        return

    events = [dict(r) for r in rows]
    report = format_daily_report(events, title_prefix="BẢN TIN SỰ KIỆN 7 NGÀY TỚI")
    await send_split_messages(update, report)


async def cmd_tinh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /tinh <tên tỉnh>: Lọc sự kiện theo tỉnh/thành miền Nam."""
    init_db()
    if not context.args:
        await update.message.reply_text(
            "Vui lòng nhập tên tỉnh. Ví dụ: <code>/tinh Cần Thơ</code> hoặc <code>/tinh Tây Ninh</code>",
            parse_mode="HTML",
        )
        return

    province_query = " ".join(context.args).strip()
    today_str = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM events WHERE province LIKE ? AND raw_date >= ? ORDER BY raw_date ASC LIMIT 10",
        (f"%{province_query}%", today_str),
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text(
            f"Không tìm thấy sự kiện nào sắp tới tại tỉnh: <b>{province_query}</b>",
            parse_mode="HTML",
        )
        return

    events = [dict(r) for r in rows]
    report = format_daily_report(
        events, title_prefix=f"SỰ KIỆN TẠI {province_query.upper()}"
    )
    await send_split_messages(update, report)


async def cmd_sukien(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /sukien <từ khóa>: Tìm kiếm sự kiện theo từ khóa."""
    init_db()
    if not context.args:
        await update.message.reply_text(
            "Vui lòng nhập từ khóa. Ví dụ: <code>/sukien pháo hoa</code> hoặc <code>/sukien concert</code>",
            parse_mode="HTML",
        )
        return

    keyword = " ".join(context.args).strip()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM events WHERE (title LIKE ? OR location LIKE ?) ORDER BY id DESC LIMIT 10",
        (f"%{keyword}%", f"%{keyword}%"),
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text(
            f"Không tìm thấy sự kiện chứa từ khóa: <b>{keyword}</b>",
            parse_mode="HTML",
        )
        return

    events = [dict(r) for r in rows]
    report = format_daily_report(
        events, title_prefix=f'TÌM KIẾM SỰ KIỆN: "{keyword}"'
    )
    await send_split_messages(update, report)


# ==========================================
# CHỨC NĂNG XUẤT EXCEL THEO TUẦN / THÁNG
# ==========================================


async def cmd_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /excel [tuan/thang]: Xuất danh sách sự kiện ra file Excel và gửi qua Telegram."""
    init_db()

    time_frame = "tuan"
    if context.args and context.args[0].lower() in ["thang", "month", "30"]:
        time_frame = "thang"

    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    if time_frame == "thang":
        end_date = (today + timedelta(days=30)).strftime("%Y-%m-%d")
        period_title = "30 NGÀY TỚI (THÁNG)"
        filename_prefix = "Su_Kien_Theo_Thang"
    else:
        end_date = (today + timedelta(days=7)).strftime("%Y-%m-%d")
        period_title = "7 NGÀY TỚI (TUẦN)"
        filename_prefix = "Su_Kien_Theo_Tuan"

    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT 
            priority as 'Mức Ưu Tiên',
            event_date as 'Ngày Diễn Ra',
            province as 'Tỉnh/Thành',
            title as 'Tên Sự Kiện',
            location as 'Địa Điểm Chi Tiết',
            scale as 'Quy Mô',
            source_name as 'Nguồn Báo',
            link as 'Đường Link Gốc'
        FROM events 
        WHERE raw_date >= ? AND raw_date <= ? 
        ORDER BY raw_date ASC
    """
    df = pd.read_sql_query(query, conn, params=(today_str, end_date))
    conn.close()

    if df.empty:
        await update.message.reply_text(
            f"Không có dữ liệu sự kiện nào trong <b>{period_title}</b> để xuất file Excel.",
            parse_mode="HTML",
        )
        return

    os.makedirs("data", exist_ok=True)
    excel_file_path = os.path.join(
        "data", f"{filename_prefix}_{today.strftime('%d%m%Y')}.xlsx"
    )

    with pd.ExcelWriter(excel_file_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Danh Sách Sự Kiện", index=False)

    caption_text = (
        f"📊 <b>BÁO CÁO XUẤT EXCEL SỰ KIỆN MIỀN NAM</b>\n\n🗓️ Khoảng thời gian:"
        f" <b>{period_title}</b>\n📈 Tổng số ghi nhận: <b>{len(df)} sự kiện</b>"
    )

    await update.message.reply_document(
        document=open(excel_file_path, "rb"),
        filename=os.path.basename(excel_file_path),
        caption=caption_text,
        parse_mode="HTML",
    )


async def cmd_excel_thang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh tắt /excel_thang để xuất nhanh Excel theo tháng."""
    context.args = ["thang"]
    await cmd_excel(update, context)


def start_bot_polling():
    """Khởi chạy Bot lắng nghe 24/7 toàn bộ các lệnh."""
    token = str(TELEGRAM_BOT_TOKEN).strip() if TELEGRAM_BOT_TOKEN else ""
    if token.startswith("bot"):
        token = token[3:]

    if not token:
        logger.error("Chưa cấu hình TELEGRAM_BOT_TOKEN trong file .env!")
        return

    app = ApplicationBuilder().token(token).build()

    # Đăng ký các Handler lệnh
    app.add_handler(CommandHandler("homnay", cmd_homnay))
    app.add_handler(CommandHandler("tuannay", cmd_tuannay))
    app.add_handler(CommandHandler("tinh", cmd_tinh))
    app.add_handler(CommandHandler("sukien", cmd_sukien))
    app.add_handler(CommandHandler("excel", cmd_excel))
    app.add_handler(CommandHandler("excel_thang", cmd_excel_thang))

    logger.info(
        "🤖 Bot Telegram đang chạy lắng nghe các lệnh (/homnay, /tuannay, /tinh,"
        " /sukien, /excel, /excel_thang)..."
    )
    app.run_polling()