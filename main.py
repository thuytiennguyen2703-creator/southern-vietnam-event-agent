import os
import sys
import time
import logging
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# 1. Thêm thư mục gốc vào sys.path để import chuẩn các module trong src/
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# 2. Cấu hình Logging & Tắt log rác từ httpx/telegram
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(name)s] %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)

# 3. Import các hàm từ thư mục src/
from src.database import init_db
from src.bot_handler import start_bot_polling, send_daily_event_report
# Nếu bạn có module cào dữ liệu/parser trong src, import vào đây:
# from src.parser import run_full_pipeline  

# -------------------------------------------------------------
# HTTP Server nhẹ cho Render Health Check (Port Binding)
# -------------------------------------------------------------
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Southern Vietnam Event Agent is Live & Running!")

    def log_message(self, format, *args):
        return  # Tắt log HTTP rác

def start_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logging.info(f"🌐 HTTP Health Check Server đang chạy tại cổng {port}")
    server.serve_forever()

# -------------------------------------------------------------
# Luồng Lập lịch Cào dữ liệu & Gửi báo cáo tự động hàng ngày
# -------------------------------------------------------------
def daily_scheduler_loop():
    TARGET_HOUR = 7  # Gửi báo cáo lúc 07:00 sáng
    last_run_day = None

    logging.info(f"⏰ Scheduler đã khởi động (Chạy định kỳ {TARGET_HOUR}:00 AM hàng ngày)...")
    
    while True:
        now = datetime.now()
        if now.hour == TARGET_HOUR and last_run_day != now.date():
            logging.info("🚀 Đến giờ hẹn! Bắt đầu cào dữ liệu & gửi báo cáo hàng ngày...")
            try:
                # Nếu có hàm cào dữ liệu, mở comment dòng dưới:
                # run_full_pipeline()
                
                # Gửi báo cáo sự kiện qua Telegram
                send_daily_event_report()
                
                last_run_day = now.date()
                logging.info("✅ Hoàn tất gửi báo cáo hàng ngày!")
            except Exception as e:
                logging.error(f"❌ Lỗi trong quá trình chạy luồng hàng ngày: {e}")

        time.sleep(60)

# -------------------------------------------------------------
# Khởi chạy toàn bộ hệ thống
# -------------------------------------------------------------
if __name__ == "__main__":
    # Khởi tạo Database
    init_db()

    # 2. CHẠY CÀO DỮ LIỆU NGAY LẦN ĐẦU KHỞI ĐỘNG (Để có data dùng ngay)
    logging.info("🔄 Đang tiến hành cào dữ liệu ban đầu cho Bot...")
    try:
        from src.parser import run_full_pipeline  # Thay bằng hàm cào dữ liệu/Gemini parser của bạn
        run_full_pipeline()
        logging.info("✅ Cào dữ liệu ban đầu thành công!")
    except Exception as e:
        logging.error(f"⚠️ Lỗi khi cào dữ liệu ban đầu: {e}")

    logging.info("🌟 Đang khởi động Event Agent System...")

    # Luồng 1: HTTP Server cho Render Port Check
    t_http = threading.Thread(target=start_health_check_server, daemon=True)
    t_http.start()

    # Luồng 2: Scheduler cào dữ liệu & gửi tin nhắn hàng ngày
    t_scheduler = threading.Thread(target=daily_scheduler_loop, daemon=True)
    t_scheduler.start()

    # Luồng 3 (Luồng chính): Chạy Telegram Bot
    logging.info("🤖 Bot Telegram đang chạy ngầm 24/7...")
    try:
        start_bot_polling()
    except (KeyboardInterrupt, SystemExit):
        logging.info("✅ Đã dừng Bot Telegram an toàn.")