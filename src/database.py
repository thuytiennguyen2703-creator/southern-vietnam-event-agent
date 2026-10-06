import sqlite3
from datetime import datetime, timedelta

from src.config import DATABASE_PATH


def get_connection():
    """
    Tạo kết nối tới SQLite database.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Khởi tạo database và các bảng cần thiết.
    """

    conn = get_connection()

    # Bảng lưu sự kiện
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            province TEXT,
            location TEXT,
            start_time TEXT,
            end_time TEXT,
            expected_attendance INTEGER,
            fireworks INTEGER DEFAULT 0,
            source_url TEXT UNIQUE,
            source_name TEXT,
            priority TEXT,
            priority_score INTEGER DEFAULT 0,
            created_at TEXT
        )
        """
    )

    # Bảng lưu lịch sử cảnh báo sự kiện lớn
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS alert_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_key TEXT NOT NULL UNIQUE,
            event_name TEXT NOT NULL,
            sent_at TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def normalize_text(value):
    """
    Chuẩn hóa text để phục vụ deduplicate.
    """
    if value is None:
        return ""

    return " ".join(
        str(value).strip().lower().split()
    )


def normalize_url(url):
    """
    Chuẩn hóa URL cơ bản.
    """
    if not url:
        return ""

    return str(url).strip().rstrip("/")


def event_dedup_key(event):
    """
    Tạo khóa deduplicate cho event.

    Ưu tiên:
    name + province + start_time

    Vì cùng một sự kiện có thể xuất hiện
    trên nhiều báo với URL khác nhau.
    """

    name = normalize_text(
        event.get("name")
    )

    province = normalize_text(
        event.get("province")
    )

    start_time = normalize_text(
        event.get("start_time")
    )

    return (
        name,
        province,
        start_time,
    )


def deduplicate_events(events):
    """
    Loại các event trùng nhau trong một batch.

    Nếu cùng event xuất hiện nhiều lần,
    giữ bản đầu tiên.
    """

    unique_events = []
    seen = set()

    for event in events:
        key = event_dedup_key(event)

        if key in seen:
            continue

        seen.add(key)
        unique_events.append(event)

    return unique_events


def deduplicate_results(rows):
    """
    Deduplicate kết quả lấy từ database.

    SQLite có thể chứa nhiều source cho cùng
    một event nếu chúng được lưu bằng URL khác nhau.
    """

    unique = []
    seen = set()

    for row in rows:
        row_dict = dict(row)

        key = event_dedup_key(row_dict)

        if key in seen:
            continue

        seen.add(key)
        unique.append(row_dict)

    return unique


def save_events(events):
    """
    Lưu danh sách event vào database.

    Event trùng source_url sẽ không được lưu lại.

    Returns:
        saved: số event mới
        duplicated: số event bị bỏ vì trùng
    """

    if not events:
        return 0, 0

    events = deduplicate_events(events)

    saved = 0
    duplicated = 0

    conn = get_connection()

    for event in events:
        source_url = normalize_url(
            event.get("source_url")
        )

        if not source_url:
            continue

        try:
            cursor = conn.execute(
                """
                INSERT INTO events (
                    name,
                    province,
                    location,
                    start_time,
                    end_time,
                    expected_attendance,
                    fireworks,
                    source_url,
                    source_name,
                    priority,
                    priority_score,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.get("name"),
                    event.get("province"),
                    event.get("location"),
                    event.get("start_time"),
                    event.get("end_time"),
                    event.get("expected_attendance"),
                    1 if event.get("fireworks") else 0,
                    source_url,
                    event.get("source_name"),
                    event.get("priority"),
                    event.get("priority_score", 0),
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                ),
            )

            if cursor.rowcount > 0:
                saved += 1

        except sqlite3.IntegrityError:
            duplicated += 1

    conn.commit()
    conn.close()

    return saved, duplicated


def parse_event_datetime(value):
    """
    Chuyển string ISO datetime thành datetime.
    """

    if not value:
        return None

    try:
        return datetime.fromisoformat(
            str(value).replace("Z", "")
        )
    except (ValueError, TypeError):
        return None


def get_upcoming_events(days=7):
    """
    Lấy các event trong 7 ngày tới.

    Bao gồm:
    1. Event chưa bắt đầu trong khoảng 7 ngày.
    2. Event đã bắt đầu nhưng vẫn đang diễn ra.

    Ví dụ:
    Event 06–08/10.

    Nếu hiện tại là 07/10:
    -> vẫn phải được trả về.

    Nếu hiện tại là 09/10:
    -> không còn được trả về.
    """

    now = datetime.now()

    start_of_day = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    end_date = start_of_day + timedelta(
        days=days
    )

    conn = get_connection()

    cursor = conn.execute(
        """
        SELECT
            id,
            name,
            province,
            location,
            start_time,
            end_time,
            expected_attendance,
            fireworks,
            source_url,
            source_name,
            priority,
            priority_score,
            created_at
        FROM events
        WHERE
            start_time IS NOT NULL
            AND (
                (
                    start_time >= ?
                    AND start_time <= ?
                )
                OR
                (
                    start_time < ?
                    AND end_time IS NOT NULL
                    AND end_time >= ?
                )
            )
        ORDER BY
            CASE
                WHEN start_time IS NULL THEN 1
                ELSE 0
            END,
            start_time ASC,
            priority_score DESC
        """,
        (
            start_of_day.isoformat(
                timespec="seconds"
            ),
            end_date.isoformat(
                timespec="seconds"
            ),
            start_of_day.isoformat(
                timespec="seconds"
            ),
            now.isoformat(
                timespec="seconds"
            ),
        ),
    )

    rows = cursor.fetchall()

    conn.close()

    return deduplicate_results(rows)


def get_events_today():
    """
    Lấy các event đang diễn ra hoặc sẽ diễn ra trong hôm nay.

    Bao gồm:
    - Event bắt đầu hôm nay.
    - Event đã bắt đầu trước hôm nay nhưng chưa kết thúc.
    """

    now = datetime.now()

    start_of_day = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    end_of_day = start_of_day.replace(
        hour=23,
        minute=59,
        second=59,
    )

    conn = get_connection()

    cursor = conn.execute(
        """
        SELECT
            id,
            name,
            province,
            location,
            start_time,
            end_time,
            expected_attendance,
            fireworks,
            source_url,
            source_name,
            priority,
            priority_score,
            created_at
        FROM events
        WHERE
            (
                start_time >= ?
                AND start_time <= ?
            )
            OR
            (
                start_time < ?
                AND end_time IS NOT NULL
                AND end_time >= ?
            )
        ORDER BY
            start_time ASC,
            priority_score DESC
        """,
        (
            start_of_day.isoformat(
                timespec="seconds"
            ),
            end_of_day.isoformat(
                timespec="seconds"
            ),
            start_of_day.isoformat(
                timespec="seconds"
            ),
            now.isoformat(
                timespec="seconds"
            ),
        ),
    )

    rows = cursor.fetchall()

    conn.close()

    return deduplicate_results(rows)


def get_events_by_province(province):
    """
    Lấy event theo tỉnh.

    Bao gồm:
    - Event sắp diễn ra.
    - Event đang diễn ra.
    - Event chưa có ngày cụ thể.
    """

    if not province:
        return []

    now = datetime.now()

    conn = get_connection()

    cursor = conn.execute(
        """
        SELECT
            id,
            name,
            province,
            location,
            start_time,
            end_time,
            expected_attendance,
            fireworks,
            source_url,
            source_name,
            priority,
            priority_score,
            created_at
        FROM events
        WHERE
            province = ?
            AND (
                start_time IS NULL
                OR start_time >= ?
                OR (
                    start_time < ?
                    AND end_time IS NOT NULL
                    AND end_time >= ?
                )
            )
        ORDER BY
            CASE
                WHEN start_time IS NULL THEN 1
                ELSE 0
            END,
            start_time ASC,
            priority_score DESC
        """,
        (
            province,
            now.isoformat(
                timespec="seconds"
            ),
            now.isoformat(
                timespec="seconds"
            ),
            now.isoformat(
                timespec="seconds"
            ),
        ),
    )

    rows = cursor.fetchall()

    conn.close()

    return deduplicate_results(rows)


def search_events(keyword):
    """
    Tìm event theo từ khóa.

    Tìm trong:
    - tên event
    - tỉnh
    - địa điểm
    """

    if not keyword:
        return []

    keyword = keyword.strip()

    pattern = f"%{keyword}%"

    now = datetime.now()

    conn = get_connection()

    cursor = conn.execute(
        """
        SELECT
            id,
            name,
            province,
            location,
            start_time,
            end_time,
            expected_attendance,
            fireworks,
            source_url,
            source_name,
            priority,
            priority_score,
            created_at
        FROM events
        WHERE
            (
                name LIKE ?
                OR province LIKE ?
                OR location LIKE ?
            )
            AND (
                start_time IS NULL
                OR start_time >= ?
                OR (
                    start_time < ?
                    AND end_time IS NOT NULL
                    AND end_time >= ?
                )
            )
        ORDER BY
            CASE
                WHEN start_time IS NULL THEN 1
                WHEN start_time >= ? THEN 0
                WHEN end_time IS NOT NULL
                     AND end_time >= ? THEN 0
                ELSE 2
            END,
            start_time ASC,
            priority_score DESC
        """,
        (
            pattern,
            pattern,
            pattern,
            now.isoformat(
                timespec="seconds"
            ),
            now.isoformat(
                timespec="seconds"
            ),
            now.isoformat(
                timespec="seconds"
            ),
        ),
    )

    rows = cursor.fetchall()

    conn.close()

    return deduplicate_results(rows)


def get_high_priority_events():
    """
    Lấy các event có priority cao.

    Bao gồm:
    - Event sắp diễn ra.
    - Event đang diễn ra.

    Không lấy event đã kết thúc.
    """

    now = datetime.now()

    conn = get_connection()

    cursor = conn.execute(
        """
        SELECT
            id,
            name,
            province,
            location,
            start_time,
            end_time,
            expected_attendance,
            fireworks,
            source_url,
            source_name,
            priority,
            priority_score,
            created_at
        FROM events
        WHERE
            priority = 'high'
            AND (
                start_time IS NULL
                OR start_time >= ?
                OR (
                    start_time < ?
                    AND end_time IS NOT NULL
                    AND end_time >= ?
                )
            )
        ORDER BY
            CASE
                WHEN start_time IS NULL THEN 1
                ELSE 0
            END,
            start_time ASC,
            priority_score DESC
        """,
        (
            now.isoformat(
                timespec="seconds"
            ),
            now.isoformat(
                timespec="seconds"
            ),
            now.isoformat(
                timespec="seconds"
            ),
        ),
    )

    rows = cursor.fetchall()

    conn.close()

    return deduplicate_results(rows)


def has_alert_been_sent(alert_key):
    """
    Kiểm tra cảnh báo này đã được gửi chưa.
    """

    conn = get_connection()

    row = conn.execute(
        """
        SELECT 1
        FROM alert_history
        WHERE alert_key = ?
        LIMIT 1
        """,
        (alert_key,),
    ).fetchone()

    conn.close()

    return row is not None


def mark_alert_sent(alert_key, event_name):
    """
    Đánh dấu một cảnh báo đã gửi thành công.
    """

    conn = get_connection()

    conn.execute(
        """
        INSERT OR IGNORE INTO alert_history (
            alert_key,
            event_name,
            sent_at
        )
        VALUES (?, ?, ?)
        """,
        (
            alert_key,
            event_name,
            datetime.now().isoformat(
                timespec="seconds"
            ),
        ),
    )

    conn.commit()
    conn.close()


from datetime import datetime, timedelta
from openpyxl import Workbook


def export_events_to_excel(
    mode: str = "week",
    output_path: str = "data/events_export.xlsx",
):
    """
    Xuất danh sách sự kiện ra Excel.

    mode:
    - week: 7 ngày tới
    - month: tháng hiện tại
    """

    now = datetime.now()

    if mode == "week":
        start_date = now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        end_date = start_date + timedelta(days=7)

    elif mode == "month":
        start_date = now.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        if start_date.month == 12:
            end_date = start_date.replace(
                year=start_date.year + 1,
                month=1,
            )
        else:
            end_date = start_date.replace(
                month=start_date.month + 1,
            )

    else:
        raise ValueError(
            "mode phải là 'week' hoặc 'month'."
        )

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            name,
            province,
            location,
            start_time,
            end_time,
            expected_attendance,
            priority,
            source_url
        FROM events
        WHERE
            (
                start_time IS NULL
                OR start_time < ?
            )
            AND
            (
                end_time IS NULL
                OR end_time >= ?
            )
        ORDER BY
            start_time ASC,
            name ASC
        """,
        (
            end_date.isoformat(),
            start_date.isoformat(),
        ),
    )

    rows = cursor.fetchall()

    conn.close()

    workbook = Workbook()

    worksheet = workbook.active

    worksheet.title = "Sự kiện"

    headers = [
        "Tên sự kiện",
        "Tỉnh",
        "Địa điểm",
        "Bắt đầu",
        "Kết thúc",
        "Quy mô dự kiến",
        "Ưu tiên",
        "Nguồn",
    ]

    worksheet.append(headers)

    for row in rows:
        worksheet.append([
            row["name"],
            row["province"],
            row["location"],
            row["start_time"],
            row["end_time"],
            row["expected_attendance"],
            row["priority"],
            row["source_url"],
        ])

    # Độ rộng cột
    column_widths = {
        "A": 45,
        "B": 20,
        "C": 40,
        "D": 22,
        "E": 22,
        "F": 18,
        "G": 15,
        "H": 25,
        "I": 60,
    }

    for column, width in column_widths.items():
        worksheet.column_dimensions[
            column
        ].width = width

    # Cố định dòng tiêu đề
    worksheet.freeze_panes = "A2"

    # Bật bộ lọc
    worksheet.auto_filter.ref = (
        worksheet.dimensions
    )

    workbook.save(output_path)

    return output_path, len(rows)