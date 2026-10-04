import os
import time
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# Import các hàm từ module của bạn
from bot_handler import run_bot, send_daily_event_report # Hàm chạy bot và gửi báo cáo hàng ngày
from parser import run_full_pipeline # Hàm cào web, dùng Gemini bóc tách, lưu SQLite/Excel

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# -------------------------------------------------------------
# 1. Luồng HTTP Server nhẹ để Render kiểm tra Port (Health Check)
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
# 2. Luồng Lập lịch Cào dữ liệu & Gửi báo cáo tự động hàng ngày
# -------------------------------------------------------------
def daily_scheduler_loop():
    """
    Luồng ngầm chạy 24/7 kiểm tra giờ để cào dữ liệu & tự động gửi tin nhắn báo cáo hàng ngày.
    """
    TARGET_HOUR = 7  # Ví dụ: Tự động chạy cào & gửi tin nhắn vào 07:00 sáng hàng ngày
    last_run_day = None

    logging.info(f"⏰ Scheduler đã khởi động (Lịch cào & gửi báo cáo cố định lúc {TARGET_HOUR}:00 AM hàng ngày)...")
    
    while True:
        now = datetime.now()
        # Kiểm tra nếu đúng giờ cài đặt và hôm nay chưa chạy
        if now.hour == TARGET_HOUR and last_run_day != now.date():
            logging.info("🚀 Đến giờ hẹn! Bắt đầu luồng cào dữ liệu mới & cập nhật Database...")
            try:
                # 1. Chạy pipeline cào web + Gemini AI
                run_full_pipeline()
                
                # 2. Gửi thông báo sự kiện mới/hôm nay trực tiếp qua Telegram
                send_daily_event_report()
                
                last_run_day = now.date()
                logging.info("✅ Hoàn tất luồng cào dữ liệu và gửi thông báo hàng ngày!")
            except Exception as e:
                logging.error(f"❌ Lỗi trong quá trình chạy luồng hàng ngày: {e}")

        time.sleep(60)  # Kiểm tra mỗi 1 phút một lần

# -------------------------------------------------------------
# 3. Luồng Khởi chạy Hệ thống Chính
# -------------------------------------------------------------
if __name__ == "__main__":
    logging.info("🌟 Đang khởi động Event Agent System...")

    # Luồng 1: Chạy HTTP Server ngầm cho Render Port Binding
    t_http = threading.Thread(target=start_health_check_server, daemon=True)
    t_http.start()

    # Luồng 2: Chạy Scheduler cào dữ liệu & gửi tin nhắn tự động hàng ngày
    t_scheduler = threading.Thread(target=daily_scheduler_loop, daemon=True)
    t_scheduler.start()

    # Luồng 3 (Luồng chính): Chạy Telegram Bot nhận lệnh tra cứu (/homnay, /tuannay, /excel,...)
    logging.info("🤖 Đang kết nối Bot Telegram...")
    run_bot()