import os
from pathlib import Path
from dotenv import load_dotenv

# Tải các biến môi trường từ file .env
load_dotenv()

# Đường dẫn thư mục gốc dự án
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = os.path.join(BASE_DIR, "data")

# Tự động tạo thư mục data nếu chưa tồn tại
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "events.db")

# Cấu hình Telegram Bot Token & Chat ID
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Danh sách nguồn RSS công khai (Đã tối ưu hóa URL hoạt động ổn định)
RSS_SOURCES = [
    # ---- Báo điện tử lớn (RSS) ----
    {
        "name": "VnExpress - Du lịch",
        "url": "https://vnexpress.net/rss/du-lich.rss"
    },
    {
        "name": "VnExpress - Giải trí",
        "url": "https://vnexpress.net/rss/giai-tri.rss"
    },
    {
        "name": "VnExpress - Thể thao",
        "url": "https://vnexpress.net/rss/the-thao.rss"
    },
    {
        "name": "Tuổi Trẻ - Du lịch",
        "url": "https://tuoitre.vn/rss/du-lich.rss"
    },
    {
        "name": "Tuổi Trẻ - Văn hóa",
        "url": "https://tuoitre.vn/rss/van-hoa.rss"
    },
    {
        "name": "Thanh Niên - Du lịch",
        "url": "https://thanhnien.vn/rss/du-lich.rss"
    },
    {
        "name": "Thanh Niên - Văn hóa",
        "url": "https://thanhnien.vn/rss/van-hoa.rss"
    },
    {
        "name": "Tiền Phong - Giải trí",
        "url": "https://tienphong.vn/rss/giai-tri-36.rss"
    },
    {
        "name": "Báo Dân Trí - Giải trí",
        "url": "https://dantri.com.vn/rss/giai-tri.rss"
    },
    {
        "name": "Báo Người Lao Động - Văn hóa",
        "url": "https://nld.com.vn/rss/van-hoa-van-nghe.rss"
    },

    # ---- Báo địa phương ----
    {
        "name": "Báo Tây Ninh - Văn hóa",
        "url": "https://baotayninh.vn/rss/news/van-hoa.rss",
    },
    {
        "name": "Báo Tây Ninh - Du lịch",
        "url": "https://baotayninh.vn/rss/news/du-lich.rss",
    },
    {
        "name": "Báo Tây Ninh - Sự kiện",
        "url": "https://baotayninh.vn/rss/news/van-de-su-kien.rss",
    },
    {
        "name": "Cổng TTĐT Vĩnh Long",
        "url": "https://vinhlong.gov.vn/rss/tintuc.rss",
    }
]

# Bộ từ khóa lọc đúng sự kiện, lễ hội, concert, đêm nhạc
EVENT_KEYWORDS = [
    "lễ hội", "festival", "concert", "đại nhạc hội", "show diễn", 
    "đêm nhạc", "bắn pháo hoa", "pháo hoa", "sự kiện", "triển lãm", 
    "hội chợ", "giải chạy", "marathon", "liveshow", "carnival", 
    "kỷ niệm", "chương trình nghệ thuật", "hội thi", "liên hoan", "múa lân"
]

# Danh sách các tỉnh/thành thuộc khu vực Miền Nam (Đông Nam Bộ & Tây Nam Bộ)
SOUTHERN_PROVINCES = [
    "An Giang", "Bạc Liêu", "Bến Tre", "Cà Mau", "Cần Thơ", 
    "Đồng Tháp", "Hậu Giang", "Kiên Giang", "Long An", "Sóc Trăng", 
    "Tiền Giang", "Trà Vinh", "Vĩnh Long", "Bà Rịa - Vũng Tàu", "Bà Rịa", "Vũng Tàu",
    "Bình Dương", "Bình Phước", "Đồng Nai", "Tây Ninh", 
    "TP.HCM", "TPHCM", "Hồ Chí Minh", "Sài Gòn"
]