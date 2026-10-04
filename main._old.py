import logging
from src.database import init_db, save_event, get_unsent_events, mark_as_sent
from src.scraper import fetch_all_sources
from src.parser import process_articles
from src.bot_handler import format_daily_report, send_telegram_message

# Cấu hình log hệ thống
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def run_pipeline():
    logging.info("=== BẮT ĐẦU CHU TRÌNH THU THẬP VÀ XỬ LÝ SỰ KIỆN ===")
    
    # 1. Khởi tạo Database nếu chưa có
    init_db()
    
    # 2. Thu thập dữ liệu thô từ các nguồn RSS
    raw_articles = fetch_all_sources()
    logging.info(f"Đã cào được {len(raw_articles)} bài viết thô từ các nguồn.")
    
    # 3. Lọc đúng sự kiện miền Nam & Trích xuất thông tin chi tiết
    events = process_articles(raw_articles)
    logging.info(f"Đã lọc & trích xuất được {len(events)} sự kiện miền Nam phù hợp.")
    
    # 4. Lưu vào CSDL (Loại bỏ các tin đã trùng lặp)
    new_events = []
    for event in events:
        if save_event(event):
            new_events.append(event)
            
    logging.info(f"Thêm mới {len(new_events)} sự kiện chưa trùng lặp vào CSDL.")
    
    # Nếu không có tin mới thì kết thúc chu trình
    if not new_events:
        logging.info("Không có sự kiện mới để phát bản tin.")
        return

    # 5. Cảnh báo riêng ngay lập tức cho sự kiện quy mô lớn ([CAO])
    high_priority_events = [e for e in new_events if e.get("priority") == "CAO"]
    if high_priority_events:
        logging.info(f"Phát hiện {len(high_priority_events)} sự kiện quy mô lớn [CAO]. Đang gửi cảnh báo...")
        alert_msg = "🚨 <b>CẢNH BÁO SỰ KIỆN QUY MÔ LỚN / BẮN PHÁO HOA</b> 🚨\n\n"
        for e in high_priority_events:
            alert_msg += f"📍 <b>{e.get('province', 'Miền Nam')}</b>: {e.get('title', '')}\n"
            if e.get("event_date"):
                alert_msg += f"🗓️ Ngày: {e.get('event_date')}\n"
            if e.get("location"):
                alert_msg += f"📍 Địa điểm: {e.get('location')}\n"
            if e.get("scale"):
                alert_msg += f"👥 Quy mô: {e.get('scale')}\n"
            alert_msg += f"🔗 Nguồn: {e.get('link', '')}\n\n"
            alert_msg += "───────────────────\n\n"
            
        send_telegram_message(alert_msg)

    # 6. Gửi bản tin tổng hợp tự động (lấy tối đa 15 sự kiện mới nhất để gửi)
    report_events = new_events[:15]
    report_text = format_daily_report(report_events, title_prefix="BẢN TIN SỰ KIỆN MIỀN NAM")
    
    if send_telegram_message(report_text):
        # Cập nhật trạng thái đã gửi trong DB để không gửi lại lần sau
        unsent = get_unsent_events()
        for item in unsent:
            mark_as_sent(item["id"])
        logging.info("Gửi bản tin tự động thành công!")
    else:
        logging.error("Gửi bản tin thất bại!")

if __name__ == "__main__":
    run_pipeline()