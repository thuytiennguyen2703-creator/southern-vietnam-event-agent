from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from src.database import (
    get_events_today,
    get_upcoming_events,
    get_events_by_province,
    search_events,
)

import os

from src.database import export_events_to_excel

# ============================================================
# FORMAT HELPERS
# ============================================================

def format_date_range(
    start_time: str | None,
    end_time: str | None,
) -> str:
    """
    Format thời gian ngắn gọn:
    17–18/10
    17/10
    Chưa xác định
    """

    if not start_time:
        return "Chưa xác định"

    try:
        start = datetime.fromisoformat(start_time)

        if not end_time:
            return start.strftime("%d/%m")

        end = datetime.fromisoformat(end_time)

        if start.date() == end.date():
            return start.strftime("%d/%m")

        if start.year == end.year and start.month == end.month:
            return f"{start.day:02d}–{end.day:02d}/{start.month:02d}"

        if start.year == end.year:
            return (
                f"{start.day:02d}/{start.month:02d}"
                f"–{end.day:02d}/{end.month:02d}"
            )

        return (
            f"{start.strftime('%d/%m/%Y')}"
            f"–{end.strftime('%d/%m/%Y')}"
        )

    except (ValueError, TypeError):
        return "Chưa xác định"


def format_priority(event: dict) -> str:
    """
    Quy đổi priority sang nhãn ngắn gọn.
    """

    if event.get("priority") == "high":
        return "CAO"

    return "THƯỜNG"


def format_scale(event: dict) -> str | None:
    """
    Format quy mô:
    ~20.000 người
    ~20.000 người · có bắn pháo hoa
    """

    attendance = event.get("expected_attendance")
    fireworks = event.get("fireworks")

    parts = []

    if attendance:
        parts.append(
            f"~{attendance:,} người"
        )

    if fireworks:
        parts.append(
            "có bắn pháo hoa"
        )

    if not parts:
        return None

    return " · ".join(parts)


def format_event(event: dict) -> str:
    """
    Format một event theo format bản tin.
    """

    priority = format_priority(event)

    date_text = format_date_range(
        event.get("start_time"),
        event.get("end_time"),
    )

    province = event.get("province") or "Chưa xác định"

    name = event.get(
        "name",
        "Không có tên",
    )

    location = event.get("location")

    lines = []

    # Dòng 1
    lines.append(
        f"<b>[{priority}] {date_text} · {province}</b>"
    )

    # Tên sự kiện
    lines.append(
        f"<b>{name}</b>"
    )

    # Địa điểm
    if location:
        lines.append(
            f"Địa điểm: {location}"
        )
    else:
        lines.append(
            "Địa điểm: Chưa xác định"
        )

    # Quy mô
    scale = format_scale(event)

    if scale:
        lines.append(
            f"Quy mô: {scale}"
        )

    # Nguồn
    source_url = event.get("source_url")

    if source_url:
        lines.append(
            f'Nguồn: <a href="{source_url}">Xem bài gốc</a>'
        )

    return "\n".join(lines)


def format_news_header(
    events: list[dict],
    title: str = "BẢN TIN SỰ KIỆN MIỀN NAM",
) -> str:
    """
    Header cho bản tin.
    """

    now = datetime.now()

    weekday_names = {
        0: "Thứ Hai",
        1: "Thứ Ba",
        2: "Thứ Tư",
        3: "Thứ Năm",
        4: "Thứ Sáu",
        5: "Thứ Bảy",
        6: "Chủ Nhật",
    }

    weekday = weekday_names[now.weekday()]

    date_text = now.strftime(
        "%d/%m/%Y"
    )

    high_count = sum(
        1
        for event in events
        if event.get("priority") == "high"
    )

    if high_count:
        count_text = (
            f"{len(events)} sự kiện "
            f"({high_count} quy mô lớn)"
        )
    else:
        count_text = (
            f"{len(events)} sự kiện"
        )

    return (
        f"<b>{title} — {weekday} {date_text}</b>\n"
        f"{'7 ngày tới: ' if title == 'BẢN TIN SỰ KIỆN MIỀN NAM' else ''}"
        f"{count_text}"
    )


def format_event_list(
    events: list[dict],
    title: str | None = None,
    include_header: bool = False,
) -> str:
    """
    Format danh sách event.

    include_header=True:
        thêm header bản tin miền Nam.

    title:
        tiêu đề riêng cho /homnay, /tinh, /sukien...
    """

    if not events:

        if include_header:
            return (
                format_news_header(events)
                + "\n\n"
                "Không có sự kiện phù hợp."
            )

        return (
            f"<b>{title or 'KẾT QUẢ'}</b>\n\n"
            "Không tìm thấy sự kiện phù hợp."
        )

    sections = []

    if include_header:
        sections.append(
            format_news_header(events)
        )

    elif title:
        sections.append(
            f"<b>{title}</b>"
        )

    for event in events:
        sections.append(
            format_event(event)
        )

    return "\n\n".join(sections)


# ============================================================
# COMMANDS
# ============================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = (
        "👋 <b>Event Bot</b>\n\n"
        "Bot giúp tra cứu các sự kiện, lễ hội "
        "và sự kiện đông người tại khu vực phía Nam.\n\n"
        "📅 <b>/homnay</b> — Sự kiện hôm nay\n"
        "📆 <b>/tuannay</b> — Sự kiện 7 ngày tới\n"
        "📍 <b>/tinh &lt;tỉnh/thành&gt;</b> — Theo tỉnh/thành\n"
        "🔎 <b>/sukien &lt;từ khóa&gt;</b> — Tìm kiếm sự kiện\n"
        "📊 <b>/excel tuan</b> hoặc <b>/excel thang</b> — Xuất danh sách sự kiện ra Excel\n\n"
        "Ví dụ:\n"
        "<code>/tinh An Giang</code>\n"
        "<code>/sukien lễ hội</code>"
    )

    await update.message.reply_text(
        message,
        parse_mode="HTML",
    )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = (
        "<b>Các lệnh có thể sử dụng</b>\n\n"
        "📅 <code>/homnay</code>\n"
        "Xem các sự kiện diễn ra hôm nay.\n\n"
        "📆 <code>/tuannay</code>\n"
        "Xem các sự kiện trong 7 ngày tới.\n\n"
        "📍 <code>/tinh An Giang</code>\n"
        "Xem sự kiện theo tỉnh/thành.\n\n"
        "🔎 <code>/sukien lễ hội</code>\n"
        "Tìm kiếm theo tên, tỉnh hoặc địa điểm.\n\n"
        "📊 <code>/excel tuan</code> hoặc <code>/excel thang</code>\n"
        "Xuất danh sách sự kiện ra Excel.\n\n"
    )

    await update.message.reply_text(
        message,
        parse_mode="HTML",
    )


async def today_command(update, context):
    events = get_events_today()
    message = format_event_list(events, include_header=True)
    await update.message.reply_text(
        message,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def week_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    events = get_upcoming_events(7)

    message = format_event_list(
        events,
        include_header=True,
    )

    await update.message.reply_text(
        message,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def province_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not context.args:
        await update.message.reply_text(
            "⚠️ Vui lòng nhập tỉnh/thành.\n\n"
            "Ví dụ:\n"
            "<code>/tinh An Giang</code>",
            parse_mode="HTML",
        )
        return

    province = " ".join(context.args)

    events = get_events_by_province(
        province,
        days=30,
    )

    message = format_event_list(
        events,
        title=f"SỰ KIỆN TẠI {province.upper()}",
    )

    await update.message.reply_text(
        message,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def search_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not context.args:
        await update.message.reply_text(
            "⚠️ Vui lòng nhập từ khóa.\n\n"
            "Ví dụ:\n"
            "<code>/sukien Nguyễn Trung Trực</code>\n"
            "<code>/sukien lễ hội</code>",
            parse_mode="HTML",
        )
        return

    keyword = " ".join(context.args)

    events = search_events(
        keyword,
        limit=20,
    )

    message = format_event_list(
        events,
        title=f"KẾT QUẢ: {keyword}",
    )

    await update.message.reply_text(
        message,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )



async def excel_command(
    update,
    context,
):
    """
    Xuất danh sách sự kiện ra Excel.

    /excel tuan
    /excel thang
    """

    if not context.args:
        await update.message.reply_text(
            "Cách dùng:\n"
            "/excel tuan - Xuất sự kiện 7 ngày tới\n"
            "/excel thang - Xuất sự kiện tháng hiện tại"
        )
        return

    mode = context.args[0].lower()

    if mode not in ["tuan", "thang"]:
        await update.message.reply_text(
            "Tham số không hợp lệ.\n\n"
            "Dùng:\n"
            "/excel tuan\n"
            "/excel thang"
        )
        return

    db_mode = "week" if mode == "tuan" else "month"

    try:
        output_path, count = export_events_to_excel(
            mode=db_mode,
        )

        if count == 0:
            await update.message.reply_text(
                "Không có sự kiện để xuất Excel."
            )
            return

        with open(
            output_path,
            "rb",
        ) as excel_file:

            await update.message.reply_document(
                document=excel_file,
                filename=os.path.basename(
                    output_path
                ),
                caption=(
                    f"📊 Danh sách sự kiện "
                    f"{'7 ngày tới' if mode == 'tuan' else 'tháng hiện tại'}\n"
                    f"📌 Tổng cộng: {count} sự kiện"
                ),
            )

    except Exception as error:
        await update.message.reply_text(
            f"❌ Không thể xuất Excel: {error}"
        )