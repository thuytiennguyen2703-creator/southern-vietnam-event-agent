import os

from dotenv import load_dotenv


# Đọc các biến trong file .env
load_dotenv()


# =========================
# Telegram
# =========================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# =========================
# Database
# =========================

DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    "data/events.db"
)


# =========================
# Các tỉnh/thành cần theo dõi
# =========================

SOUTHERN_PROVINCES = [
    "TP. Hồ Chí Minh",
    "Đồng Nai",
    "Tây Ninh",
    "An Giang",
    "Đồng Tháp",
    "Vĩnh Long",
    "Cần Thơ",
    "Cà Mau",
]