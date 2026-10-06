from datetime import datetime

from sources import SOURCES
from src.scraper import scrape_source
from src.parser import parse_articles
from src.ai_extractor import extract_events
from src.database import (
    init_db,
    save_events,
)
from src.config import SOUTHERN_PROVINCES
from src.logger import logger


ALLOWED_EVENT_TYPES = {
    "le_hoi",
    "van_hoa_du_lich",
    "the_thao",
    "am_nhac",
    "phao_hoa",
    "hoi_cho_trien_lam",
    "hoi_nghi_lon",
    "ha_tang_du_lich_dong_khach",
    "nghi_le",
}


def collect_articles():
    """
    Thu thập bài viết từ tất cả nguồn.

    Nếu một nguồn lỗi:
    - Ghi lỗi vào logger.
    - Lưu thông tin lỗi vào source_errors.
    - Bỏ qua nguồn đó.
    - Tiếp tục xử lý các nguồn còn lại.

    Trả về:
        all_articles: danh sách bài viết thu thập được.
        source_errors: danh sách nguồn bị lỗi.
    """

    all_articles = []
    source_errors = []

    print("=" * 70)
    print("SCRAPING SOURCES")
    print("=" * 70)

    for source in SOURCES:
        source_name = source["name"]

        print()
        print(f"Source : {source_name}")
        print(f"Type   : {source['type']}")

        logger.info(
            f"Bắt đầu thu thập nguồn: {source_name}"
        )

        try:
            articles = scrape_source(source)

            print(
                f"Found  : {len(articles)} articles"
            )

            all_articles.extend(articles)

            logger.info(
                f"Thu thập thành công: "
                f"{source_name} "
                f"({len(articles)} bài)"
            )

        except Exception as e:
            error_type = type(e).__name__
            error_message = str(e)

            print(
                f"ERROR  : "
                f"{error_type}: {error_message}"
            )

            print(
                "SKIP   : "
                "Bỏ qua source này và tiếp tục."
            )

            logger.error(
                f"Thu thập thất bại: "
                f"{source_name} | "
                f"{error_type}: {error_message}",
                exc_info=True,
            )

            source_errors.append({
                "source_name": source_name,
                "source_url": source.get(
                    "url",
                    "",
                ),
                "error_type": error_type,
                "error": error_message,
            })

    logger.info(
        f"Hoàn tất thu thập nguồn: "
        f"{len(all_articles)} bài | "
        f"{len(source_errors)} nguồn lỗi"
    )

    return all_articles, source_errors


def parse_event_date(date_value):
    """
    Chuyển start_time/end_time thành datetime.

    Trả về None nếu không parse được.
    """

    if not date_value:
        return None

    try:
        return datetime.fromisoformat(
            str(date_value).replace(
                "Z",
                "",
            )
        )

    except (
        ValueError,
        TypeError,
    ):
        return None


def is_past_event(event: dict) -> bool:
    """
    Kiểm tra event đã kết thúc hoàn toàn hay chưa.

    - Có end_time:
        Chỉ loại khi end_time đã qua.
    - Không có end_time nhưng có start_time:
        Loại nếu start_time đã qua.
    - Không có start_time:
        Giữ nguyên vì chưa đủ dữ liệu để kết luận.
    """

    now = datetime.now()

    end_time = parse_event_date(
        event.get("end_time")
    )

    if end_time is not None:
        return end_time < now

    start_time = parse_event_date(
        event.get("start_time")
    )

    if start_time is not None:
        return start_time < now

    return False


def validate_event(event: dict) -> bool:
    """
    Validation cuối cùng.

    Quan điểm:
    - Event thật nhưng thiếu metadata vẫn giữ.
    - Event không phải sự kiện thì loại.
    - Event ngoài phạm vi tỉnh thì loại.
    - Event quá khứ hoàn toàn thì loại.
    """

    # --------------------------------------------------
    # 1. AI phải xác nhận đây là event
    # --------------------------------------------------

    if not event.get("is_event"):
        print(
            f"[VALIDATION REJECT] "
            f"AI không xác nhận là sự kiện: "
            f"{event.get('name')}"
        )

        return False

    # --------------------------------------------------
    # 2. Event type hợp lệ
    # --------------------------------------------------

    event_type = event.get(
        "event_type"
    )

    if event_type not in ALLOWED_EVENT_TYPES:
        print(
            f"[VALIDATION REJECT] "
            f"Loại sự kiện không hợp lệ: "
            f"{event.get('name')}"
        )

        return False

    # --------------------------------------------------
    # 3. Province phải thuộc phạm vi project
    # --------------------------------------------------

    province = event.get(
        "province"
    )

    if province not in SOUTHERN_PROVINCES:
        print(
            f"[VALIDATION REJECT] "
            f"Ngoài phạm vi tỉnh: "
            f"{event.get('name')}"
        )

        return False

    # --------------------------------------------------
    # 4. Event phải có tên
    # --------------------------------------------------

    if not event.get("name"):
        print(
            "[VALIDATION REJECT] "
            "Sự kiện không có tên."
        )

        return False

    # --------------------------------------------------
    # 5. Event phải có source
    # --------------------------------------------------

    if not event.get("source_url"):
        print(
            f"[VALIDATION REJECT] "
            f"Không có source URL: "
            f"{event.get('name')}"
        )

        return False

    # --------------------------------------------------
    # 6. Fireworks consistency
    # --------------------------------------------------

    if event.get("fireworks"):
        if event_type != "phao_hoa":
            print(
                f"[VALIDATION REJECT] "
                f"fireworks=true nhưng "
                f"event_type không phải phao_hoa: "
                f"{event.get('name')}"
            )

            return False

    if event_type == "phao_hoa":
        if not event.get("fireworks"):
            print(
                f"[VALIDATION REJECT] "
                f"event_type=phao_hoa nhưng "
                f"fireworks=false: "
                f"{event.get('name')}"
            )

            return False

    # --------------------------------------------------
    # 7. Event đã diễn ra hoàn toàn
    # --------------------------------------------------

    if is_past_event(event):
        print(
            f"[VALIDATION REJECT] "
            f"Event đã diễn ra: "
            f"{event.get('name')} "
            f"({event.get('start_time')})"
        )

        return False

    # --------------------------------------------------
    # 8. Không yêu cầu location/time/attendance
    # --------------------------------------------------
    #
    # Event thật nhưng thiếu metadata vẫn được giữ.
    #
    # Ví dụ:
    #
    # Lễ hội Nguyễn Trung Trực
    # province = An Giang
    # location = None
    # start_time = None
    #
    # => VẪN VALID.
    #

    return True


def validate_events(
    events: list[dict],
) -> tuple[list[dict], list[dict]]:
    """
    Chia events thành valid và rejected.
    """

    valid_events = []
    rejected_events = []

    for event in events:
        if validate_event(event):
            valid_events.append(event)
        else:
            rejected_events.append(event)

    return (
        valid_events,
        rejected_events,
    )


def print_event(event: dict):
    """
    In event để kiểm tra.
    """

    print()
    print(
        f"Name       : "
        f"{event.get('name')}"
    )

    print(
        f"Type       : "
        f"{event.get('event_type')}"
    )

    print(
        f"Province   : "
        f"{event.get('province')}"
    )

    print(
        f"Location   : "
        f"{event.get('location')}"
    )

    print(
        f"Start      : "
        f"{event.get('start_time')}"
    )

    print(
        f"End        : "
        f"{event.get('end_time')}"
    )

    print(
        f"Attendance : "
        f"{event.get('expected_attendance')}"
    )

    print(
        f"Fireworks  : "
        f"{event.get('fireworks')}"
    )

    print(
        f"Priority   : "
        f"{event.get('priority')}"
    )

    print(
        f"Source     : "
        f"{event.get('source_url')}"
    )


def print_rejected_event(event: dict):
    """
    In chi tiết event bị reject.
    """

    print()
    print(
        f"Name       : "
        f"{event.get('name')}"
    )

    print(
        f"Type       : "
        f"{event.get('event_type')}"
    )

    print(
        f"Is event   : "
        f"{event.get('is_event')}"
    )

    print(
        f"Province   : "
        f"{event.get('province')}"
    )

    print(
        f"Location   : "
        f"{event.get('location')}"
    )

    print(
        f"Start      : "
        f"{event.get('start_time')}"
    )

    print(
        f"End        : "
        f"{event.get('end_time')}"
    )

    print(
        f"Attendance : "
        f"{event.get('expected_attendance')}"
    )

    print(
        f"Fireworks  : "
        f"{event.get('fireworks')}"
    )

    print(
        f"Priority   : "
        f"{event.get('priority')}"
    )

    print(
        f"Source     : "
        f"{event.get('source_url')}"
    )


def run_pipeline():
    """
    Chạy toàn bộ pipeline:

    Scraper
        ↓
    Parser
        ↓
    Gemini AI
        ↓
    Validation
        ↓
    SQLite
    """

    print()
    print("=" * 70)
    print("EVENT COLLECTION PIPELINE")
    print("=" * 70)

    logger.info(
        "========== BẮT ĐẦU PIPELINE =========="
    )

    # --------------------------------------------------
    # 1. DATABASE
    # --------------------------------------------------

    init_db()

    print()
    print("[1/5] Database initialized")

    logger.info(
        "Database initialized"
    )

    # --------------------------------------------------
    # 2. SCRAPER
    # --------------------------------------------------

    all_articles, source_errors = (
        collect_articles()
    )

    print()
    print(
        f"Total articles scraped: "
        f"{len(all_articles)}"
    )

    if source_errors:
        logger.warning(
            f"Có {len(source_errors)} "
            f"nguồn thu thập bị lỗi."
        )
    else:
        logger.info(
            "Tất cả nguồn thu thập thành công."
        )

    # --------------------------------------------------
    # 3. PARSER
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("PARSING EVENT ARTICLES")
    print("=" * 70)

    event_articles = parse_articles(
        all_articles
    )

    print()
    print(
        f"Event candidates: "
        f"{len(event_articles)}"
    )

    logger.info(
        f"Parser tạo "
        f"{len(event_articles)} ứng viên"
    )

    # --------------------------------------------------
    # 4. AI EXTRACTION
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("AI EXTRACTION")
    print("=" * 70)

    events = extract_events(
        event_articles
    )

    print()
    print(
        f"Events extracted by AI: "
        f"{len(events)}"
    )

    logger.info(
        f"AI trích xuất "
        f"{len(events)} sự kiện"
    )

    # --------------------------------------------------
    # 5. VALIDATION
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("EVENT VALIDATION")
    print("=" * 70)

    valid_events, rejected_events = (
        validate_events(events)
    )

    print()
    print(
        f"Valid events    : "
        f"{len(valid_events)}"
    )

    print(
        f"Rejected events : "
        f"{len(rejected_events)}"
    )

    logger.info(
        f"Validation: "
        f"{len(valid_events)} valid | "
        f"{len(rejected_events)} rejected"
    )

    # --------------------------------------------------
    # 6. SAVE
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("SAVING EVENTS")
    print("=" * 70)

    saved, duplicated = save_events(
        valid_events
    )

    print()
    print(
        f"New events saved : "
        f"{saved}"
    )

    print(
        f"Duplicates       : "
        f"{duplicated}"
    )

    logger.info(
        f"Database save: "
        f"{saved} new | "
        f"{duplicated} duplicates"
    )

    # --------------------------------------------------
    # 7. VALID EVENTS
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("VALID EVENTS")
    print("=" * 70)

    for event in valid_events:
        print_event(event)

    # --------------------------------------------------
    # 8. REJECTED EVENTS
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("REJECTED EVENTS")
    print("=" * 70)

    for event in rejected_events:
        print_rejected_event(event)

    # --------------------------------------------------
    # 9. SOURCE ERRORS
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("SOURCE ERRORS")
    print("=" * 70)

    if source_errors:
        for source_error in source_errors:
            print()
            print(
                f"Source : "
                f"{source_error.get('source_name')}"
            )

            print(
                f"URL    : "
                f"{source_error.get('source_url')}"
            )

            print(
                f"Error  : "
                f"{source_error.get('error_type')}: "
                f"{source_error.get('error')}"
            )
    else:
        print("No source errors.")

    # --------------------------------------------------
    # 10. SUMMARY
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("PIPELINE FINISHED")
    print("=" * 70)

    print()

    print(
        f"Articles scraped : "
        f"{len(all_articles)}"
    )

    print(
        f"Parser candidates: "
        f"{len(event_articles)}"
    )

    print(
        f"AI events        : "
        f"{len(events)}"
    )

    print(
        f"Valid events     : "
        f"{len(valid_events)}"
    )

    print(
        f"Rejected events  : "
        f"{len(rejected_events)}"
    )

    print(
        f"Saved events     : "
        f"{saved}"
    )

    print(
        f"Duplicates       : "
        f"{duplicated}"
    )

    print(
        f"Source errors    : "
        f"{len(source_errors)}"
    )

    print()

    logger.info(
        f"Pipeline hoàn tất: "
        f"{len(all_articles)} articles | "
        f"{len(valid_events)} valid events | "
        f"{saved} saved | "
        f"{len(source_errors)} source errors"
    )

    logger.info(
        "========== KẾT THÚC PIPELINE =========="
    )

    return (
        valid_events,
        source_errors,
    )


if __name__ == "__main__":
    run_pipeline()