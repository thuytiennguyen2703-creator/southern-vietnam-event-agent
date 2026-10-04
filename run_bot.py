import logging
import sys
from pathlib import Path

# Thêm thư mục gốc dự án vào sys.path để import chuẩn module src
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# 1. Cấu hình logging chung cho hệ thống
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(name)s] %(message)s",
)

# 2. 🔇 TẮT LOG THÔNG THƯỜNG CỦA HTTPX VÀ TELEGRAM (Chỉ hiển thị khi có WARNING/ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

from src.bot_handler import start_bot_polling
from src.database import init_db

if __name__ == "__main__":
  # Khởi tạo CSDL nếu chưa có
  init_db()

  print("==================================================")
  print("   BOT TELEGRAM TRA CỨU SỰ KIỆN MIỀN NAM        ")
  print("==================================================")
  print("Danh sách lệnh hỗ trợ:")
  print("  • /homnay          - Xem sự kiện ghi nhận hôm nay")
  print("  • /tuannay         - Xem bản tin sự kiện 7 ngày tới")
  print("  • /tinh <tên tỉnh> - Lọc sự kiện theo tỉnh/thành")
  print("  • /sukien <từ khóa>- Tìm kiếm sự kiện theo từ khóa")
  print("--------------------------------------------------")
  print("🤖 Bot đang chạy ngầm 24/7 và lắng nghe tin nhắn...")
  print("   (Đã tắt rác log polling - Bấm Ctrl+C để dừng)")
  print("==================================================\n")

  try:
    start_bot_polling()
  except (KeyboardInterrupt, SystemExit):
    print("\n✅ Đã dừng Bot Telegram an toàn.")