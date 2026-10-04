import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.bot_handler import format_daily_report, send_telegram_message
from src.config import DB_PATH
from src.database import get_unsent_events, init_db, mark_as_sent, save_event
from src.parser import process_articles
from src.scraper import fetch_all_sources

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(name)s] %(message)s",
)
logger = logging.getLogger("scheduler")


class BotScheduler:

  def __init__(self):
    # Khởi tạo AsyncIOScheduler với múi giờ Việt Nam
    self.scheduler = AsyncIOScheduler(timezone="Asia/Ho_Chi_Minh")
    self.is_running_pipeline = False

  async def job_crawl_and_alert(self):
    """Mốc 06:45 AM: Cào dữ liệu từ các nguồn RSS, lọc tin mới và gửi CẢNH BÁO KHẨN nếu phát hiện sự kiện lớn [CAO]."""
    if self.is_running_pipeline:
      logger.warning("Pipeline cào tin đang chạy, bỏ qua lần này.")
      return

    self.is_running_pipeline = True
    logger.info("🔄 [06:45 AM] Bắt đầu cào dữ liệu và kiểm tra sự kiện lớn...")

    try:
      init_db()

      # Chạy cào dữ liệu thô trong Thread riêng để không làm nghẽn Event Loop
      raw_articles = await asyncio.to_thread(fetch_all_sources)
      events = process_articles(raw_articles)

      new_events = []
      for ev in events:
        if save_event(ev):
          new_events.append(ev)

      logger.info(
          f"✅ Đã cào & lưu mới {len(new_events)} sự kiện chưa trùng lặp vào"
          " CSDL."
      )

      # Phát cảnh báo khẩn lập tức đối với sự kiện quy mô lớn ([CAO])
      high_priority = [e for e in new_events if e.get("priority") == "CAO"]
      if high_priority:
        logger.info(
            f"🚨 Phát hiện {len(high_priority)} sự kiện quy mô lớn [CAO]. Đang"
            " phát cảnh báo..."
        )
        alert_msg = (
            "🚨 <b>CẢNH BÁO SỰ KIỆN QUY MÔ LỚN / BẮN PHÁO HOA</b> 🚨\n\n"
        )
        for e in high_priority:
          alert_msg += (
              f"📍 <b>{e.get('province', 'Miền Nam')}</b>:"
              f" {e.get('title', '')}\n"
          )
          alert_msg += f"🗓️ Ngày: {e.get('event_date', 'Sắp diễn ra')}\n"
          alert_msg += f"📍 Địa điểm: {e.get('location', '')}\n"
          if e.get("scale"):
            alert_msg += f"👥 Quy mô: {e.get('scale')}\n"
          alert_msg += f"🔗 Link: {e.get('link', '')}\n\n───────────────────\n\n"

        await asyncio.to_thread(send_telegram_message, alert_msg)

    except Exception as e:
      logger.error(f"❌ Lỗi trong quá trình cào dữ liệu & cảnh báo: {e}", exc_info=True)
    finally:
      self.is_running_pipeline = False

  async def job_broadcast_morning_report(self):
    """Mốc 07:00 AM: Tổng hợp danh sách sự kiện trong 7 ngày tới và gửi BẢN TIN SÁNG TỰ ĐỘNG."""
    logger.info("☀️ [07:00 AM] Bắt đầu phát hành bản tin sáng tự động...")

    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM events WHERE DATE(created_at) >= ? ORDER BY id DESC"
        " LIMIT 15",
        (seven_days_ago,),
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
      logger.info("Không có sự kiện mới trong 7 ngày qua để gửi bản tin.")
      return

    events = [dict(r) for r in rows]
    report_text = format_daily_report(
        events, title_prefix="BẢN TIN SỰ KIỆN MIỀN NAM"
    )

    success = await asyncio.to_thread(send_telegram_message, report_text)
    if success:
      for item in events:
        mark_as_sent(item["id"])
      logger.info("✅ Đã phát hành bản tin sáng tự động thành công!")
    else:
      logger.error("❌ Lỗi khi gửi bản tin sáng tự động.")

  def setup_jobs(self):
    """Đăng ký các mốc thời gian chạy tự động trong ngày"""
    # 1. 06:45 AM mỗi ngày: Cào tin & phát cảnh báo khẩn
    self.scheduler.add_job(
        self.job_crawl_and_alert,
        trigger=CronTrigger(hour=6, minute=45),
        id="job_morning_crawl",
        name="Morning Crawl & Urgency Alert",
        replace_existing=True,
    )

    # 2. 07:00 AM mỗi ngày: Phát bản tin sáng tổng hợp
    self.scheduler.add_job(
        self.job_broadcast_morning_report,
        trigger=CronTrigger(hour=7, minute=0),
        id="job_morning_report",
        name="Broadcast Morning Bulletin",
        replace_existing=True,
    )

    logger.info("⏰ Scheduler đã đăng ký các mốc thời gian: 06:45 AM -> 07:00 AM.")

  def start(self):
    self.setup_jobs()
    self.scheduler.start()


async def main():
  bot_scheduler = BotScheduler()

  # Bật Scheduler lắng nghe mốc thời gian
  bot_scheduler.start()

  print("==================================================")
  print("   TIẾN TRÌNH LẬP LỊCH TỰ ĐỘNG ĐÃ KHỞI CHẠY       ")
  print("   - 06:45 AM: Cào tin & Cảnh báo khẩn [CAO]      ")
  print("   - 07:00 AM: Phát bản tin sáng tự động          ")
  print("   Bấm Ctrl+C để dừng chương trình.               ")
  print("==================================================")

  # Giữ cho Event Loop chạy ngầm liên tục
  while True:
    await asyncio.sleep(3600)


if __name__ == "__main__":
  try:
    asyncio.run(main())
  except (KeyboardInterrupt, SystemExit):
    print("\nĐã dừng tiến trình lập lịch an toàn.")