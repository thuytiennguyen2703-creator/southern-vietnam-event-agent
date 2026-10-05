# Southern Vietnam Event Agent

Hệ thống tự động cào tin lễ hội/sự kiện Miền Nam từ báo chí, bóc tách bằng **Gemini AI** và gửi báo cáo qua **Telegram Bot**.

---

## Tính năng chính
- **Cào tự động**: Hơn 5 nguồn báo lớn (Thanh Niên, Tuổi Trẻ, VnExpress, Dân Trí, Cổng TTĐT tỉnh,...).
- **Trích xuất AI**: Dùng RegEx & Gemini AI lấy chuẩn: *Tên sự kiện, Tỉnh, Địa điểm, Ngày, Quy mô, Link*.
- **Lịch tự động**: Gửi bản tin sự kiện 7 ngày tới vào **07:00 AM hàng ngày** qua Telegram.
- **Cảnh báo HOT**: Đánh dấu nổi bật sự kiện quy mô ≥10.000 người, pháo hoa, concert.
- **Bot tương tác**: Tra cứu sự kiện qua lệnh `/homnay`, `/tuannay`, `/tinh`, `/sukien`, `/excel`.
- **Log & Giám sát**: Tự động ghi log và kiểm tra trạng thái sức khỏe (Health Check) phục vụ cho Render & UptimeRobot.

---

## Cấu trúc thư mục
- `data/`: Chứa CSDL SQLite (`events.db`)
- `src/ai_extractor.py`: Xử lý trích xuất bằng Gemini AI
- `src/bot_handler.py`: Xử lý lệnh & gửi tin nhắn Telegram
- `src/config.py`: Biến môi trường & cấu hình từ khóa
- `src/database.py`: Quản lý SQLite database
- `src/parser.py`: Bộ lọc RegEx & chuẩn hóa dữ liệu
- `src/pipeline.py`: Luồng điều phối: Cào -> AI -> Lưu DB
- `src/scraper.py`: Cào dữ liệu RSS/HTTP
- `.env.example`: File mẫu cấu hình API Key
- `Dockerfile`: Cấu hình container
- `main.py`: File chạy chính (Scheduler, Bot, Health Server)
- `requirements.txt`: Danh sách thư viện Python

---

## Hướng dẫn cài đặt & Chạy Local

### 1. Cài đặt môi trường
git clone https://github.com/your-username/your-repo.git
cd your-repo

python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate # Linux/macOS

pip install -r requirements.txt

### 2. Cấu hình file .env
Tạo file `.env` tại thư mục gốc với nội dung:
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
GEMINI_API_KEY=your_gemini_key
PORT=8080

### 3. Chạy ứng dụng
python main.py

---

## Deploy lên Render (24/7 Free)

1. Push code lên GitHub: `git push origin main`
2. Tạo Web Service trên Render: Kết nối với GitHub Repository.
3. Cấu hình lệnh:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python main.py`
4. Thêm Environment Variables:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `GEMINI_API_KEY`
5. Bấm Create Web Service để ứng dụng tự chạy 24/7.

---

## Lệnh Tra Cứu Trên Telegram Bot
- `/homnay`: Sự kiện diễn ra hôm nay.
- `/tuannay`: Danh sách sự kiện 7 ngày tới.
- `/tinh <tên tỉnh>`: Lọc sự kiện theo tỉnh (VD: `/tinh TP.HCM`).
- `/sukien <từ khóa>`: Tìm kiếm theo từ khóa (VD: `/sukien Nhạc`).
- `/excel`: Xuất file Excel sự kiện tuần này.

---

## Lý do lựa chọn Telegram Bot API
Trong số các nền tảng nhắn tin (Telegram, Zalo OA, WhatsApp), dự án đã chọn **Telegram Bot API** làm giải pháp chính:
- **Tốc độ triển khai & Tự động hóa hoàn toàn**: BotFather cho phép khởi tạo bot chỉ trong vài giây, miễn phí 100% và không giới hạn lượt gửi tin nhắn tự động.
- **Không phát sinh chi phí & Thủ tục**: Tránh được các rào cản kiểm duyệt doanh nghiệp phức tạp, đăng ký giấy phép Official Account (như Zalo OA) hay phí gửi tin nhắn chủ động qua API.
- **Hỗ trợ tốt**: Gửi file Excel, xử lý lệnh tương tác (`/homnay`, `/tuannay`,...) mượt mà và bảo mật tốt.