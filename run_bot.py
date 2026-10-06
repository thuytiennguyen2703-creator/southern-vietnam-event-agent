from datetime import time
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from zoneinfo import ZoneInfo

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from src.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)

from src.bot_handler import (
    start_command,
    help_command,
    today_command,
    week_command,
    province_command,
    search_command,
    format_event_list,
    excel_command,
)

from src.database import get_upcoming_events, init_db
from pipeline import run_pipeline


VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


async def refresh_events(context: ContextTypes.DEFAULT_TYPE):
    """
    Chạy pipeline để cập nhật dữ liệu sự kiện trước bản tin 07:00.

    Nếu có nguồn thu thập bị lỗi thì gửi cảnh báo Telegram.
    """

    print()
    print("=" * 70)
    print("[SCHEDULER] Bắt đầu cập nhật dữ liệu sự kiện")
    print("=" * 70)

    try:
        events, source_errors = run_pipeline()

        print()
        print(
            f"[SCHEDULER] Cập nhật hoàn tất - "
            f"{len(events)} valid events"
        )

        # --------------------------------------------------
        # GỬI CẢNH BÁO KHI SOURCE BỊ LỖI
        # --------------------------------------------------

        if source_errors:

            print(
                f"[SCHEDULER] Phát hiện "
                f"{len(source_errors)} nguồn bị lỗi."
            )

            for source_error in source_errors:

                source_name = source_error.get(
                    "source_name",
                    "Không xác định",
                )

                source_url = source_error.get(
                    "source_url",
                    "",
                )

                error_type = source_error.get(
                    "error_type",
                    "UnknownError",
                )

                error_message = source_error.get(
                    "error",
                    "Không có thông tin lỗi.",
                )

                message = (
                    "⚠️ <b>CẢNH BÁO NGUỒN THU THẬP</b>\n\n"
                    f"<b>Nguồn:</b> {source_name}\n"
                    f"<b>Lỗi:</b> {error_type}\n"
                    f"<b>Chi tiết:</b> {error_message}\n"
                )

                if source_url:
                    message += (
                        f"\n🔗 <a href=\"{source_url}\">"
                        f"Mở nguồn</a>"
                    )

                message += (
                    "\n\n"
                    "Nguồn này đã được bỏ qua trong "
                    "lần thu thập hiện tại."
                )

                try:
                    await context.bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text=message,
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                    )

                    print(
                        f"[SCHEDULER] Đã gửi cảnh báo: "
                        f"{source_name}"
                    )

                except Exception as telegram_error:
                    print(
                        f"[SCHEDULER ERROR] "
                        f"Không thể gửi cảnh báo "
                        f"{source_name}: "
                        f"{telegram_error}"
                    )

        else:
            print(
                "[SCHEDULER] Không có nguồn nào bị lỗi."
            )

    except Exception as error:
        print(
            f"[SCHEDULER ERROR] "
            f"Không thể cập nhật dữ liệu: {error}"
        )


async def send_daily_bulletin(context: ContextTypes.DEFAULT_TYPE):
    """
    Đọc dữ liệu mới nhất từ SQLite và gửi bản tin 07:00.
    """
    if not TELEGRAM_CHAT_ID:
        print(
            "[SCHEDULER] TELEGRAM_CHAT_ID "
            "chưa được cấu hình."
        )
        return

    try:
        events = get_upcoming_events(days=7)

        message = format_event_list(
            events,
            include_header=True,
        )

        await context.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

        print(
            f"[SCHEDULER] Đã gửi bản tin 07:00 - "
            f"{len(events)} sự kiện"
        )

    except Exception as error:
        print(
            f"[SCHEDULER ERROR] "
            f"Không thể gửi bản tin: {error}"
        )

def start_health_server():
    port = int(os.getenv("PORT", "10000"))

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"OK")

        def do_HEAD(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()


        def log_message(self, format, *args):
            return

    server = HTTPServer(("0.0.0.0", port), HealthHandler)

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()

    print(f"Health server is running on port {port}")

def main():
    init_db()

    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN chưa được cấu hình trong .env"
        )

    if not TELEGRAM_CHAT_ID:
        raise RuntimeError(
            "TELEGRAM_CHAT_ID chưa được cấu hình trong .env"
        )

    app = (
        Application
        .builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    # --------------------------------------------------
    # TELEGRAM COMMANDS
    # --------------------------------------------------

    app.add_handler(
        CommandHandler("start", start_command)
    )

    app.add_handler(
        CommandHandler("help", help_command)
    )

    app.add_handler(
        CommandHandler("homnay", today_command)
    )

    app.add_handler(
        CommandHandler("tuannay", week_command)
    )

    app.add_handler(
        CommandHandler("tinh", province_command)
    )

    app.add_handler(
        CommandHandler("sukien", search_command)
    )

    app.add_handler(
        CommandHandler("excel", excel_command,)
    )

    # --------------------------------------------------
    # SCHEDULER
    # --------------------------------------------------

    # 06:30 - cào lại dữ liệu và cập nhật SQLite
    app.job_queue.run_daily(
        refresh_events,
        time=time(
            hour=6,
            minute=30,
            tzinfo=VIETNAM_TZ,
        ),
        name="refresh_events_0630",
    )

    # 07:00 - gửi bản tin từ dữ liệu mới nhất
    app.job_queue.run_daily(
        send_daily_bulletin,
        time=time(
            hour=7,
            minute=0,
            tzinfo=VIETNAM_TZ,
        ),
        name="daily_event_bulletin_0700",
    )

    app.job_queue.run_once(
        refresh_events,
        when=5,
        name="initial_event_refresh",
    )

    print("Telegram bot is running...")
    print(
        "Event refresh scheduled at "
        "06:30 Vietnam time."
    )
    print(
        "Daily bulletin scheduled at "
        "07:00 Vietnam time."
    )

    start_health_server()

    app.run_polling()


if __name__ == "__main__":
    main()