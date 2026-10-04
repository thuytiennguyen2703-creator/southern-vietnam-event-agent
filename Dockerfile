# 1. Sử dụng Python 3.11 bản nhẹ gọn
FROM python:3.11-slim

# 2. Đặt thư mục làm việc trong container
WORKDIR /app

# 3. Cài đặt các công cụ hệ thống cần thiết
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. Sao chép requirements.txt và cài đặt thư viện Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Sao chép toàn bộ mã nguồn vào container
COPY . .

# 6. Tạo thư mục chứa database SQLite nếu chưa có
RUN mkdir -p data

# 7. Lệnh khởi chạy Bot Telegram 24/7
CMD ["python", "main.py"]