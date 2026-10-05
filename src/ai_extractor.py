import json
import re
import time
from datetime import datetime

import os
from dotenv import load_dotenv
from google import genai

from src.config import SOUTHERN_PROVINCES


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY chưa được cấu hình trong file .env"
    )


client = genai.Client(
    api_key=GEMINI_API_KEY
)

MODEL_NAME = "gemini-3.5-flash-lite"


# ============================================================
# RATE LIMIT
# ============================================================

MAX_RETRIES = 5

DEFAULT_RETRY_SECONDS = 60

# Free Tier hiện tại của bạn:
# tối đa khoảng 15 request/phút.
REQUESTS_PER_MINUTE = 15

request_times = []


def wait_for_rate_limit():
    """
    Không gửi quá REQUESTS_PER_MINUTE request
    trong một khoảng 60 giây.
    """

    global request_times

    now = time.time()

    # Chỉ giữ các request trong 60 giây gần nhất.
    request_times = [
        timestamp
        for timestamp in request_times
        if now - timestamp < 60
    ]

    if len(request_times) >= REQUESTS_PER_MINUTE:

        oldest_request = request_times[0]

        wait_seconds = (
            60 - (now - oldest_request)
        )

        wait_seconds = max(
            wait_seconds,
            1,
        )

        print()
        print(
            f"[RATE LIMIT] Đã đạt "
            f"{REQUESTS_PER_MINUTE} request/phút."
        )

        print(
            f"[RATE LIMIT] Chờ "
            f"{wait_seconds:.1f}s..."
        )

        time.sleep(wait_seconds)

        now = time.time()

        request_times = [
            timestamp
            for timestamp in request_times
            if now - timestamp < 60
        ]


def register_request():
    request_times.append(
        time.time()
    )


def get_retry_seconds(error) -> int:
    """
    Lấy retryDelay từ lỗi Gemini nếu có.
    """

    error_text = str(error)

    match = re.search(
        r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+)s",
        error_text,
        re.IGNORECASE,
    )

    if match:
        return int(
            match.group(1)
        )

    match = re.search(
        r"retryDelay.*?(\d+)s",
        error_text,
        re.IGNORECASE,
    )

    if match:
        return int(
            match.group(1)
        )

    return DEFAULT_RETRY_SECONDS


# ============================================================
# CLEAN / NORMALIZE DATA
# ============================================================

def clean_value(value):
    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return None

    return value


def clean_number(value):
    """
    Chuyển các dạng số phổ biến về integer.

    Ví dụ:
        10000
        "10000"
        "10.000 người"
        "hơn 10.000 người"
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(value)

    text = str(value).lower().strip()

    if not text:
        return None

    # Chuẩn hóa một số cách viết phổ biến.
    text = text.replace(
        ",",
        "",
    )

    text = text.replace(
        ".",
        "",
    )

    match = re.search(
        r"\d+",
        text,
    )

    if match:
        try:
            return int(
                match.group()
            )

        except ValueError:
            return None

    return None


def normalize_datetime(value):
    """
    Chuẩn hóa thời gian về:

    YYYY-MM-DD HH:MM

    Nếu AI không cung cấp được thời gian hợp lệ
    thì trả về giá trị gốc để không tự suy đoán.
    """

    if not value:
        return None

    value = str(value).strip()

    if not value:
        return None

    value = value.replace(
        "T",
        " ",
    )

    try:
        dt = datetime.fromisoformat(
            value
        )

        return dt.strftime(
            "%Y-%m-%d %H:%M"
        )

    except ValueError:
        return value


def normalize_province(value):
    """
    Chỉ chấp nhận tỉnh/thành thuộc phạm vi theo dõi.
    """

    if not value:
        return None

    value = str(value).strip()

    aliases = {
        "Hồ Chí Minh": "TP. Hồ Chí Minh",
        "TP.HCM": "TP. Hồ Chí Minh",
        "TP HCM": "TP. Hồ Chí Minh",
        "TP.HCM.": "TP. Hồ Chí Minh",
        "Sài Gòn": "TP. Hồ Chí Minh",
        "Saigon": "TP. Hồ Chí Minh",
    }

    value = aliases.get(
        value,
        value,
    )

    for province in SOUTHERN_PROVINCES:

        if value.lower() == province.lower():
            return province

    return None


def normalize_event_type(value):
    """
    Chỉ cho phép các loại sự kiện nằm trong phạm vi project.
    """

    if not value:
        return None

    value = str(value).strip().lower()

    allowed_types = {
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

    if value in allowed_types:
        return value

    return None


def normalize_bool(value):
    """
    Tránh lỗi:

        bool("false") == True

    """

    if isinstance(value, bool):
        return value

    if value is None:
        return False

    text = str(value).strip().lower()

    return text in {
        "true",
        "1",
        "yes",
        "có",
        "co",
    }


# ============================================================
# PROMPT
# ============================================================

def build_prompt(article: dict) -> str:

    title = article.get(
        "title",
        "",
    )

    summary = article.get(
        "summary",
        "",
    )

    content = article.get(
        "content",
        "",
    )

    province = article.get(
        "province"
    )

    provinces_text = ", ".join(
        SOUTHERN_PROVINCES
    )

    return f"""
Bạn là hệ thống AI dùng để phân loại và trích xuất
DỮ LIỆU SỰ KIỆN cho một bot theo dõi các sự kiện
đông người tại miền Nam Việt Nam.

MỤC TIÊU:

Chỉ giữ lại các bài báo nói về MỘT SỰ KIỆN CỤ THỂ
thuộc phạm vi theo dõi.

Không được biến một bài báo thông thường thành sự kiện.

============================================================
CÁC LOẠI SỰ KIỆN ĐƯỢC THEO DÕI
============================================================

1. Lễ hội truyền thống, tín ngưỡng
   Ví dụ:
   - vía Bà
   - cúng đình
   - lễ hội truyền thống
   - Ok Om Bok
   - Chôl Chnăm Thmây

   event_type = "le_hoi"

2. Sự kiện văn hóa, du lịch, lễ kỷ niệm,
   khai mạc/bế mạc cấp tỉnh.

   event_type = "van_hoa_du_lich"

3. Sự kiện thể thao.

   event_type = "the_thao"

4. Sự kiện ca nhạc, đại nhạc hội,
   concert, liveshow.

   event_type = "am_nhac"

5. Bắn pháo hoa, countdown, đếm ngược,
   chương trình chào năm mới có pháo hoa.

   event_type = "phao_hoa"

6. Hội chợ, triển lãm.

   event_type = "hoi_cho_trien_lam"

7. Hội nghị lớn:
   - cấp tỉnh
   - cấp vùng
   - quốc gia
   - quốc tế
   - hội nghị có quy mô lớn

   Không lấy các hội nghị/hội thảo chuyên môn
   thông thường.

   event_type = "hoi_nghi_lon"

8. Sự kiện hoặc hoạt động đặc biệt tại:
   - sân bay
   - cảng
   - khu du lịch
   - khu vui chơi
   - điểm du lịch

   Chỉ chọn khi bài báo nói về một hoạt động,
   sự kiện cụ thể hoặc tình trạng đông khách
   đáng theo dõi.

   event_type = "ha_tang_du_lich_dong_khach"

9. Ngày lễ, Tết và các kỳ nghỉ dài có
   lượng người di chuyển lớn.

   event_type = "nghi_le"


============================================================
CÁC BÀI PHẢI LOẠI
============================================================

is_event = false nếu bài là:

- đời tư cá nhân
- sinh nhật cá nhân
- đám cưới cá nhân
- kỷ niệm cưới
- kỷ niệm cá nhân
- tiểu sử người nổi tiếng
- phỏng vấn
- bài phân tích
- bài bình luận
- bài xu hướng
- bài tổng hợp
- bài xếp hạng
- top địa điểm
- review
- check-in
- gợi ý du lịch
- kinh nghiệm du lịch
- giới thiệu địa điểm chung
- giới thiệu điểm đến
- bài về doanh thu du lịch
- bài về tăng trưởng du lịch
- bài về mục tiêu đón khách
- bài thống kê lượng khách nhưng không có
  sự kiện cụ thể
- bài về dự án
- bài quy hoạch
- bài xây dựng
- bài giải phóng mặt bằng
- hội nghị chuyên môn thông thường
- hội thảo khoa học
- hội thảo chuyên ngành
- tin chính trị/hành chính thông thường
- phát biểu của lãnh đạo
- bài tổng kết hoặc báo cáo
- tin không nói về một sự kiện cụ thể
- bất kỳ nội dung nào không thuộc
  các event_type được phép.


============================================================
QUY TẮC QUAN TRỌNG
============================================================

1. Không được tự suy đoán.

2. Không được tự thêm thông tin không có trong bài.

3. Nếu bài không nói rõ thông tin nào,
   trả về null.

4. "Kỷ niệm" của một cá nhân KHÔNG phải
   sự kiện cần theo dõi.

5. "Lễ kỷ niệm" cấp tỉnh/công cộng có tổ chức
   sự kiện thì ĐƯỢC theo dõi.

6. Không được biến tên địa điểm thành tên sự kiện.

7. Không được coi một khu du lịch là một sự kiện.

8. Không được coi việc khách du lịch tăng
   là một sự kiện nếu bài không nói về
   một hoạt động/sự kiện cụ thể.

9. Không được coi mọi "hội nghị" là sự kiện lớn.

10. Pháo hoa chỉ true khi bài thực sự đề cập
    đến pháo hoa hoặc bắn/trình diễn pháo hoa.

11. expected_attendance chỉ lấy số người liên quan
    trực tiếp đến quy mô/dự kiến tham dự/đón
    của sự kiện.

12. Không lấy các con số khác trong bài làm
    số người tham dự.

13. Nếu chỉ nói:
    "đông người",
    "đông du khách",
    "đông khách"

    nhưng không có con số cụ thể:

    expected_attendance = null

14. Có thể quy đổi:

    "hàng nghìn người" = 1000

    "hàng chục nghìn người" = 10000

    "hàng trăm nghìn người" = 100000

15. "hơn 10.000 người" = 10000.

16. Nếu có địa điểm cụ thể:
    - quảng trường
    - sân vận động
    - công viên
    - khu du lịch
    - phường
    - xã
    - bến tàu
    - cảng
    - sân bay

    thì đưa vào location.

17. Nếu chỉ biết tỉnh mà không có địa điểm cụ thể:

    location = null

18. Thời gian phải lấy từ bài báo.

19. Không được tự đoán giờ.

20. Nếu chỉ có ngày:

    có thể dùng 00:00

    nhưng không được nói rằng bài báo
    thực sự công bố giờ 00:00.

21. Nếu chỉ có ngày bắt đầu:

    end_time = null

22. Nếu bài nói sự kiện đã diễn ra trong quá khứ,
    vẫn trích xuất thời gian được bài báo đề cập.

23. province bắt buộc thuộc:

    {provinces_text}


============================================================
QUYẾT ĐỊNH is_event
============================================================

is_event = true

CHỈ KHI:

- bài nói về một sự kiện cụ thể
- sự kiện thuộc một trong các event_type được phép
- sự kiện nằm trong phạm vi miền Nam Việt Nam.

Nếu không chắc chắn:

is_event = false


============================================================
THÔNG TIN BÀI BÁO
============================================================

Tiêu đề:
{title}

Tóm tắt:
{summary}

Tỉnh đã được parser xác định:
{province}

Nội dung:
{content}


============================================================
OUTPUT
============================================================

Chỉ trả về DUY NHẤT JSON.

Không markdown.
Không ```json.
Không giải thích.
Không thêm text bên ngoài JSON.

Nếu là sự kiện:

{{
    "is_event": true,
    "event_type": "le_hoi",
    "name": "...",
    "province": "...",
    "location": "...",
    "start_time": "YYYY-MM-DD HH:MM",
    "end_time": "YYYY-MM-DD HH:MM",
    "expected_attendance": 10000,
    "fireworks": false
}}

Nếu KHÔNG phải sự kiện:

{{
    "is_event": false,
    "event_type": null,
    "name": null,
    "province": null,
    "location": null,
    "start_time": null,
    "end_time": null,
    "expected_attendance": null,
    "fireworks": false
}}
"""


# ============================================================
# GEMINI EXTRACTION
# ============================================================

def extract_event(
    article: dict,
) -> dict | None:

    prompt = build_prompt(
        article
    )

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        try:

            # ----------------------------------------
            # Rate limit
            # ----------------------------------------

            wait_for_rate_limit()

            register_request()

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config={
                    "temperature": 0,
                    "response_mime_type": "application/json",
                },
            )

            raw_text = response.text.strip()

            if not raw_text:
                print(
                    f"[AI EMPTY] "
                    f"{article.get('title', '')}"
                )

                return None


            # ----------------------------------------
            # Parse JSON
            # ----------------------------------------

            try:

                data = json.loads(
                    raw_text
                )

            except json.JSONDecodeError:

                raw_text = raw_text.replace(
                    "```json",
                    "",
                )

                raw_text = raw_text.replace(
                    "```",
                    "",
                )

                raw_text = raw_text.strip()

                try:

                    data = json.loads(
                        raw_text
                    )

                except json.JSONDecodeError:

                    print(
                        "[AI JSON ERROR] "
                        f"Không đọc được JSON: "
                        f"{article.get('title', '')}"
                    )

                    return None


            if not isinstance(
                data,
                dict,
            ):
                return None


            # ----------------------------------------
            # AI xác định đây có phải sự kiện không
            # ----------------------------------------

            is_event = normalize_bool(
                data.get(
                    "is_event",
                    False,
                )
            )

            if not is_event:

                print(
                    "[AI REJECT] "
                    "Không phải sự kiện cần theo dõi: "
                    f"{article.get('title', '')}"
                )

                return None


            # ----------------------------------------
            # Chuẩn hóa event type
            # ----------------------------------------

            event_type = normalize_event_type(
                data.get(
                    "event_type"
                )
            )

            if not event_type:

                print(
                    "[AI REJECT] "
                    "event_type không hợp lệ: "
                    f"{article.get('title', '')}"
                )

                return None


            # ----------------------------------------
            # Province
            # ----------------------------------------

            ai_province = normalize_province(
                data.get(
                    "province"
                )
            )

            parser_province = normalize_province(
                article.get(
                    "province"
                )
            )

            # Province từ parser được ưu tiên
            if parser_province:
                province = parser_province
            else:
                province = ai_province


            # Không có tỉnh thì reject.
            if not province:

                print(
                    "[AI REJECT] "
                    "Không xác định được tỉnh: "
                    f"{article.get('title', '')}"
                )

                return None


            # ----------------------------------------
            # Fireworks
            # ----------------------------------------

            fireworks = normalize_bool(
                data.get(
                    "fireworks",
                    False,
                )
            )


            # Nếu fireworks = true thì event_type
            # bắt buộc phải là phao_hoa.
            if fireworks and event_type != "phao_hoa":

                print(
                    "[AI REJECT] "
                    "fireworks=true nhưng "
                    "event_type không phải phao_hoa: "
                    f"{article.get('title', '')}"
                )

                return None


            # ----------------------------------------
            # Name
            # ----------------------------------------

            name = clean_value(
                data.get(
                    "name"
                )
            )

            if not name:

                name = article.get(
                    "title",
                    "",
                ).strip()


            if not name:

                print(
                    "[AI REJECT] "
                    "Không có tên sự kiện."
                )

                return None


            # ----------------------------------------
            # Tạo event
            # ----------------------------------------

            event = {
                "is_event": True,

                "event_type": event_type,

                "name": name,

                "province": province,

                "location": clean_value(
                    data.get(
                        "location"
                    )
                ),

                "start_time": normalize_datetime(
                    data.get(
                        "start_time"
                    )
                ),

                "end_time": normalize_datetime(
                    data.get(
                        "end_time"
                    )
                ),

                "expected_attendance": clean_number(
                    data.get(
                        "expected_attendance"
                    )
                ),

                "fireworks": fireworks,
            }


            # ----------------------------------------
            # Metadata từ parser/article
            # ----------------------------------------

            event["source_name"] = article.get(
                "source_name",
                "",
            )

            event["source_url"] = article.get(
                "url",
                "",
            )

            event["published"] = article.get(
                "published",
                "",
            )

            event["categories"] = article.get(
                "categories",
                [],
            )

            event["priority_score"] = article.get(
                "priority_score",
                0,
            )

            event["priority"] = article.get(
                "priority",
                "normal",
            )


            return event


        # ====================================================
        # RATE LIMIT / RETRY
        # ====================================================

        except Exception as e:

            error_text = str(e)

            is_rate_limit = (
                "429" in error_text
                or "RESOURCE_EXHAUSTED"
                in error_text
                or "quota"
                in error_text.lower()
            )

            if is_rate_limit:

                retry_seconds = get_retry_seconds(
                    e
                )

                # Thêm vài giây đệm.
                retry_seconds += 2

                print()
                print(
                    "[AI RATE LIMIT]"
                )

                print(
                    f"Article : "
                    f"{article.get('title', '')}"
                )

                print(
                    f"Attempt : "
                    f"{attempt}/{MAX_RETRIES}"
                )

                print(
                    f"Waiting : "
                    f"{retry_seconds}s"
                )

                time.sleep(
                    retry_seconds
                )

                continue


            # ----------------------------------------
            # Lỗi khác
            # ----------------------------------------

            print(
                f"[AI ERROR] "
                f"{article.get('title', '')}: "
                f"{type(e).__name__}: {e}"
            )

            return None


    # ========================================================
    # HẾT RETRY
    # ========================================================

    print(
        "[AI FAILED] "
        f"Không xử lý được sau "
        f"{MAX_RETRIES} lần: "
        f"{article.get('title', '')}"
    )

    return None


# ============================================================
# EXTRACT ALL EVENTS
# ============================================================

def extract_events(
    articles: list[dict],
) -> list[dict]:

    results = []

    for index, article in enumerate(
        articles,
        start=1,
    ):

        print(
            f"[AI] {index}/{len(articles)} "
            f"{article.get('title', '')}"
        )

        event = extract_event(
            article
        )

        if event:
            results.append(
                event
            )

    return results