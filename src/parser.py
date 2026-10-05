import re

from src.config import SOUTHERN_PROVINCES


# ============================================================
# 1. NHÓM SỰ KIỆN CẦN THEO DÕI
# ============================================================

EVENT_CATEGORIES = {
    "le_hoi": [
        "lễ hội",
        "hội lễ",
        "lễ vía",
        "vía bà",
        "cúng đình",
        "lễ đình",
        "lễ hội đình",
        "ok om bok",
        "chôl chnăm thmây",
        "đua ghe ngo",
        "lễ cầu an",
        "lễ cầu ngư",
        "lễ hội truyền thống",
        "lễ hội dân gian",
        "lễ hội tín ngưỡng",
    ],

    "van_hoa_du_lich": [
        "sự kiện văn hóa",
        "sự kiện du lịch",
        "ngày hội du lịch",
        "ngày hội văn hóa",
        "tuần lễ du lịch",
        "festival",
        "lễ kỷ niệm",
        "chương trình văn hóa",
        "chương trình du lịch",
        "liên hoan văn hóa",
        "liên hoan nghệ thuật",
        "khai mạc lễ hội",
        "bế mạc lễ hội",
        "khai mạc tuần lễ",
        "bế mạc tuần lễ",
    ],

    "the_thao": [
        "giải chạy",
        "marathon",
        "half marathon",
        "ultra marathon",
        "giải đua",
        "đua thuyền",
        "đua ghe",
        "đua xe",
        "giải bóng đá",
        "giải bóng chuyền",
        "vòng chung kết",
        "giải thể thao quốc gia",
        "giải thể thao quốc tế",
    ],

    "am_nhac": [
        "đêm nhạc",
        "concert",
        "mega concert",
        "liveshow",
        "đại nhạc hội",
        "nhạc hội",
        "show diễn",
        "chương trình âm nhạc",
        "sự kiện âm nhạc",
    ],

    "phao_hoa": [
        "pháo hoa",
        "bắn pháo hoa",
        "trình diễn pháo hoa",
        "pháo hoa nghệ thuật",
        "pháo hoa tầm cao",
        "pháo hoa tầm thấp",
        "countdown",
        "đếm ngược",
        "chào năm mới",
        "giao thừa",
    ],

    "hoi_cho_trien_lam": [
        "hội chợ",
        "hội chợ thương mại",
        "hội chợ du lịch",
        "triển lãm",
        "triển lãm quốc tế",
        "triển lãm du lịch",
        "expo",
        "festival thương mại",
    ],

    "hoi_nghi_lon": [
        "hội nghị quốc gia",
        "hội nghị quốc tế",
        "hội nghị cấp tỉnh",
        "hội nghị cấp vùng",
        "hội nghị quy mô lớn",
        "hội nghị lớn",
        "diễn đàn quốc gia",
        "diễn đàn quốc tế",
        "diễn đàn cấp vùng",
    ],

    "ha_tang_du_lich_dong_khach": [
        "sân bay",
        "cảng biển",
        "cảng",
        "bến tàu",
        "bến cảng",
        "khu du lịch",
        "điểm du lịch",
        "khu vui chơi",
        "khu nghỉ dưỡng",
    ],

    "nghi_le": [
        "ngày lễ",
        "nghỉ lễ",
        "kỳ nghỉ lễ",
        "kỳ nghỉ dài",
        "nghỉ tết",
        "kỳ nghỉ tết",
        "tết nguyên đán",
        "tết dương lịch",
        "giỗ tổ hùng vương",
        "30/4",
        "1/5",
        "2/9",
    ],
}


# ============================================================
# 2. TỪ KHÓA QUY MÔ / ĐÔNG NGƯỜI
# ============================================================

CROWD_KEYWORDS = [
    "đông người",
    "đông du khách",
    "đông khách",
    "đông người tham dự",
    "đông người dân",
    "hàng nghìn người",
    "hàng ngàn người",
    "hàng vạn người",
    "hàng chục nghìn người",
    "hàng chục ngàn người",
    "hàng trăm nghìn người",
    "hàng trăm ngàn người",
    "hơn 1.000 người",
    "hơn 5.000 người",
    "hơn 10.000 người",
    "hơn 20.000 người",
    "hơn 50.000 người",
    "10.000 người",
    "20.000 người",
    "50.000 người",
    "100.000 người",
    "vạn người",
    "thu hút đông du khách",
    "thu hút hàng nghìn",
    "thu hút hàng ngàn",
    "thu hút hàng vạn",
    "dự kiến đón",
    "dự kiến thu hút",
    "quy mô lớn",
    "quy mô hàng nghìn",
    "quy mô hàng vạn",
]


# ============================================================
# 3. SỰ KIỆN ƯU TIÊN CAO
# ============================================================

HIGH_PRIORITY_KEYWORDS = [
    "pháo hoa",
    "bắn pháo hoa",
    "đại nhạc hội",
    "mega concert",
    "countdown",
    "đếm ngược",
    "hàng chục nghìn người",
    "hàng chục ngàn người",
    "hàng vạn người",
    "hơn 10.000 người",
    "hơn 20.000 người",
    "hơn 50.000 người",
    "100.000 người",
]


# ============================================================
# 4. NGỮ CẢNH KHÁCH / DU LỊCH
# ============================================================

PUBLIC_CROWD_CONTEXT = [
    "đón khách",
    "đón du khách",
    "đón hành khách",
    "lượng khách",
    "du khách",
    "hành khách",
    "khách du lịch",
    "khách tham quan",
    "cao điểm",
    "dịp lễ",
    "dịp tết",
    "kỳ nghỉ",
    "đông khách",
    "tăng khách",
    "tăng lượng khách",
    "lượng khách tăng",
    "thu hút khách",
    "thu hút du khách",
    "dự kiến đón",
    "phục vụ khách",
]


# ============================================================
# 5. TỪ KHÓA THỂ HIỆN BÀI THỰC SỰ NÓI VỀ MỘT SỰ KIỆN
# ============================================================

EVENT_INTENT_KEYWORDS = [
    "tổ chức",
    "sẽ tổ chức",
    "được tổ chức",
    "diễn ra",
    "sẽ diễn ra",
    "dự kiến diễn ra",
    "khai mạc",
    "bế mạc",
    "phát động",
    "đăng cai",
    "tham dự",
    "tham gia",
    "thi đấu",
    "trình diễn",
    "biểu diễn",
    "bắn pháo hoa",
    "đón giao thừa",
    "đếm ngược",
    "mở cửa đón khách",
    "khởi động",
    "khai trương",
    "lễ hội",
    "ngày hội",
    "festival",
    "giải chạy",
    "marathon",
    "concert",
    "liveshow",
    "đại nhạc hội",
    "hội chợ",
    "triển lãm",
    "cuộc thi",
    "giải đấu",
]


# ============================================================
# 6. BÀI DỄ BỊ NHẬN NHẦM LÀ SỰ KIỆN
# ============================================================

FALSE_POSITIVE_KEYWORDS = [
    "mục tiêu đón",
    "mục tiêu thu hút",
    "ngành du lịch",
    "thị trường du lịch",
    "thị trường khách",
    "khách quốc tế",
    "khách nội địa",
    "lượng khách quốc tế",
    "lượng khách nội địa",
    "doanh thu du lịch",
    "tăng trưởng du lịch",
    "tăng trưởng khách",
    "top ",
    "top 10",
    "top 20",
    "xếp hạng",
    "đứng đầu",
    "tốt nhất thế giới",
    "tốt nhất việt nam",
    "cẩm nang",
    "kinh nghiệm du lịch",
    "gợi ý du lịch",
    "địa điểm du lịch",
    "điểm đến hấp dẫn",
    "check-in",
    "review",
    "khám phá",
    "hành trình",
    "ẩm thực",
    "mẹo du lịch",
    "chú chó",
    "động vật",
]


# ============================================================
# 7. LOẠI BỎ TIN CHÍNH TRỊ / HỘI NGHỊ KHÔNG PHẢI SỰ KIỆN
# ============================================================

EXCLUDE_KEYWORDS = [
    "ban chấp hành trung ương",
    "bộ chính trị",
    "ban bí thư",
    "hội nghị trung ương",
    "hội nghị ban chấp hành",
    "tổng bí thư",
    "hội nghị giao ban",
    "hội nghị sơ kết",
    "hội nghị tổng kết",
    "hội nghị triển khai",
    "hội nghị trực tuyến",
    "hội thảo chuyên môn",
    "hội thảo khoa học",
    "toàn văn phát biểu",
    "phát biểu khai mạc",
    "phát biểu bế mạc",
    "phát biểu chỉ đạo",
    "quán triệt",
    "kết luận hội nghị",
    "báo cáo tại hội nghị",
    "điểm tin",
    "tin nhanh",
    "tin tức trong ngày",
    "5 phút biết hết",
    "bản tin",
    "audio",
    "dự án",
    "tiến độ dự án",
    "thủ tục",
    "giải phóng mặt bằng",
    "thi công",
    "quy hoạch",
]


# ============================================================
# 8. TIÊU ĐỀ CHỈ LÀ TRANG CHUYÊN MỤC
# ============================================================

CATEGORY_PAGE_TITLES = {
    "thể thao",
    "văn hóa",
    "du lịch",
    "giải trí",
    "tin tức",
    "thời sự",
    "kinh tế",
    "xã hội",
    "chính trị",
    "đời sống",
    "pháp luật",
    "sức khỏe",
    "giáo dục",
    "công nghệ",
}


# ============================================================
# 9. ĐỊA ĐIỂM NGOÀI PHẠM VI
# ============================================================

OUT_OF_SCOPE_LOCATIONS = [
    "hà nội",
    "thủ đô hà nội",
    "đà nẵng",
    "hải phòng",
    "huế",
    "lâm đồng",
    "đà lạt",
    "khánh hòa",
    "nha trang",
    "quảng ninh",
    "hạ long",
    "phú quốc",
    "quảng nam",
    "quảng ngãi",
    "bình định",
    "phú yên",
    "gia lai",
    "kon tum",
    "đắk lắk",
    "đắk nông",
    "thanh hóa",
    "nghệ an",
    "hà tĩnh",
    "quảng bình",
    "quảng trị",
    "thừa thiên huế",
]


# ============================================================
# 10. ĐIỂM TRỌNG SỐ
# ============================================================

CATEGORY_PRIORITY = {
    "le_hoi": 4,
    "am_nhac": 4,
    "phao_hoa": 6,
    "hoi_cho_trien_lam": 3,
    "the_thao": 3,
    "van_hoa_du_lich": 2,
    "hoi_nghi_lon": 2,
    "nghi_le": 3,
}


STRONG_EVENT_CATEGORIES = {
    "le_hoi",
    "the_thao",
    "am_nhac",
    "phao_hoa",
    "hoi_cho_trien_lam",
}


BROAD_CATEGORIES = {
    "van_hoa_du_lich",
    "nghi_le",
    "hoi_nghi_lon",
    "ha_tang_du_lich_dong_khach",
}


# ============================================================
# 11. HÀM CHUẨN HÓA
# ============================================================

def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.lower()
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def get_article_text(article: dict) -> str:
    return normalize_text(
        " ".join(
            [
                article.get("title", ""),
                article.get("summary", ""),
                article.get("content", ""),
            ]
        )
    )


def get_title_summary(article: dict) -> str:
    return normalize_text(
        " ".join(
            [
                article.get("title", ""),
                article.get("summary", ""),
            ]
        )
    )


# ============================================================
# 12. XÁC ĐỊNH TỈNH
# ============================================================

def detect_province(article: dict) -> str | None:
    if article.get("province"):
        return article["province"]

    text = get_article_text(article)

    aliases = {
        "hồ chí minh": "TP. Hồ Chí Minh",
        "tp.hcm": "TP. Hồ Chí Minh",
        "tp hcm": "TP. Hồ Chí Minh",
        "tp.hồ chí minh": "TP. Hồ Chí Minh",
        "sài gòn": "TP. Hồ Chí Minh",
        "saigon": "TP. Hồ Chí Minh",

        "đồng nai": "Đồng Nai",
        "tây ninh": "Tây Ninh",
        "an giang": "An Giang",
        "đồng tháp": "Đồng Tháp",
        "vĩnh long": "Vĩnh Long",
        "cần thơ": "Cần Thơ",
        "cà mau": "Cà Mau",
    }

    for alias, province in aliases.items():
        if normalize_text(alias) in text:
            return province

    return None


# ============================================================
# 13. KIỂM TRA BÀI NGOÀI PHẠM VI
# ============================================================

def is_obviously_out_of_scope(article: dict) -> bool:
    """
    Loại các bài rõ ràng nói về địa điểm ngoài 8 tỉnh/thành
    mục tiêu.

    Không dùng danh sách này để suy luận tỉnh cho bài,
    chỉ dùng để loại false positive rõ ràng.
    """

    text = get_article_text(article)

    target_found = any(
        normalize_text(province) in text
        for province in SOUTHERN_PROVINCES
    )

    if target_found:
        return False

    return any(
        normalize_text(location) in text
        for location in OUT_OF_SCOPE_LOCATIONS
    )


# ============================================================
# 14. KIỂM TRA TRANG CHUYÊN MỤC
# ============================================================

def is_category_page(article: dict) -> bool:
    title = normalize_text(article.get("title", ""))

    return title in CATEGORY_PAGE_TITLES


# ============================================================
# 15. KIỂM TRA BÀI CẦN LOẠI
# ============================================================

def is_excluded(article: dict) -> bool:
    text = get_article_text(article)

    return any(
        normalize_text(keyword) in text
        for keyword in EXCLUDE_KEYWORDS
    )


def is_false_positive(article: dict) -> bool:
    title_summary = get_title_summary(article)
    text = get_article_text(article)

    # Nếu tiêu đề có các mẫu rất đặc trưng của bài
    # phân tích du lịch / xếp hạng / xu hướng thì loại.
    for keyword in FALSE_POSITIVE_KEYWORDS:
        normalized_keyword = normalize_text(keyword)

        if normalized_keyword in title_summary:
            return True

    # Các bài chỉ nói về du lịch / lượng khách nhưng
    # không có dấu hiệu của một sự kiện cụ thể.
    tourism_analysis_keywords = [
        "mục tiêu đón",
        "khách quốc tế",
        "khách nội địa",
        "lượng khách",
        "doanh thu du lịch",
        "tăng trưởng du lịch",
        "thị trường khách",
    ]

    has_tourism_analysis = any(
        normalize_text(keyword) in text
        for keyword in tourism_analysis_keywords
    )

    has_event_intent = detect_event_intent(article)

    if has_tourism_analysis and not has_event_intent:
        return True

    return False


# ============================================================
# 16. PHÁT HIỆN CATEGORY
# ============================================================

def detect_categories(article: dict) -> list[str]:
    text = get_article_text(article)
    title_summary = get_title_summary(article)

    categories = []

    for category, keywords in EVENT_CATEGORIES.items():

        # Các category mạnh:
        # chỉ cần xuất hiện trong tiêu đề / nội dung.
        if category in STRONG_EVENT_CATEGORIES:
            if any(
                normalize_text(keyword) in text
                for keyword in keywords
            ):
                categories.append(category)

            continue

        # Category rộng:
        # ưu tiên keyword xuất hiện trong title/summary.
        if any(
            normalize_text(keyword) in title_summary
            for keyword in keywords
        ):
            categories.append(category)

            continue

        # Nếu keyword chỉ xuất hiện trong body,
        # phải có event intent mới giữ.
        if any(
            normalize_text(keyword) in text
            for keyword in keywords
        ) and detect_event_intent(article):
            categories.append(category)

    return categories


# ============================================================
# 17. PHÁT HIỆN Ý ĐỊNH SỰ KIỆN
# ============================================================

def detect_event_intent(article: dict) -> bool:
    text = get_article_text(article)

    return any(
        normalize_text(keyword) in text
        for keyword in EVENT_INTENT_KEYWORDS
    )


# ============================================================
# 18. PHÁT HIỆN QUY MÔ
# ============================================================

def detect_crowd(article: dict) -> bool:
    text = get_article_text(article)

    return any(
        normalize_text(keyword) in text
        for keyword in CROWD_KEYWORDS
    )


def detect_high_priority(article: dict) -> bool:
    text = get_article_text(article)

    return any(
        normalize_text(keyword) in text
        for keyword in HIGH_PRIORITY_KEYWORDS
    )


# ============================================================
# 19. PHÁT HIỆN NGỮ CẢNH ĐÔNG KHÁCH
# ============================================================

def detect_public_crowd_context(article: dict) -> bool:
    text = get_article_text(article)

    return any(
        normalize_text(keyword) in text
        for keyword in PUBLIC_CROWD_CONTEXT
    )


def is_public_infrastructure_event(
    article: dict,
    categories: list[str],
) -> bool:

    if "ha_tang_du_lich_dong_khach" not in categories:
        return False

    # Hạ tầng chỉ được coi là candidate nếu có
    # ngữ cảnh đông khách + dấu hiệu sự kiện/hoạt động.
    return (
        detect_public_crowd_context(article)
        and detect_event_intent(article)
    )


# ============================================================
# 20. KIỂM TRA BÀI CÓ PHẢI EVENT THỰC SỰ KHÔNG
# ============================================================

def is_event_article(article: dict) -> bool:

    # -----------------------------------------
    # Bước 1: loại trang chuyên mục
    # -----------------------------------------
    if is_category_page(article):
        return False

    # -----------------------------------------
    # Bước 2: loại tin chắc chắn không liên quan
    # -----------------------------------------
    if is_excluded(article):
        return False

    # -----------------------------------------
    # Bước 3: loại bài rõ ràng ngoài phạm vi
    # -----------------------------------------
    if is_obviously_out_of_scope(article):
        return False

    # -----------------------------------------
    # Bước 4: loại false positive
    # -----------------------------------------
    if is_false_positive(article):
        return False

    # -----------------------------------------
    # Bước 5: xác định category
    # -----------------------------------------
    categories = detect_categories(article)

    if not categories:
        return False

    # -----------------------------------------
    # Bước 6:
    # Các sự kiện mạnh -> giữ
    # -----------------------------------------
    if any(
        category in STRONG_EVENT_CATEGORIES
        for category in categories
    ):
        return True

    # -----------------------------------------
    # Bước 7:
    # Hạ tầng du lịch / sân bay / cảng...
    # phải có cả crowd context + event intent
    # -----------------------------------------
    if "ha_tang_du_lich_dong_khach" in categories:

        other_categories = [
            category
            for category in categories
            if category != "ha_tang_du_lich_dong_khach"
        ]

        if not other_categories:
            return is_public_infrastructure_event(
                article,
                categories,
            )

    # -----------------------------------------
    # Bước 8:
    # Category rộng phải có event intent
    # -----------------------------------------
    if any(
        category in BROAD_CATEGORIES
        for category in categories
    ):
        return detect_event_intent(article)

    return False


# ============================================================
# 21. TÍNH PRIORITY
# ============================================================

def calculate_priority_score(article: dict) -> int:

    categories = detect_categories(article)

    score = 0

    if detect_high_priority(article):
        score += 10

    if detect_crowd(article):
        score += 5

    if detect_event_intent(article):
        score += 2

    for category in categories:
        score += CATEGORY_PRIORITY.get(
            category,
            0,
        )

    return score


def detect_priority(article: dict) -> str:

    score = calculate_priority_score(article)

    if score >= 10:
        return "high"

    if score >= 5:
        return "medium"

    return "normal"


# ============================================================
# 22. CHUẨN HÓA ARTICLE
# ============================================================

def normalize_article(article: dict) -> dict:

    categories = detect_categories(article)

    return {
        "title": article.get(
            "title",
            "",
        ).strip(),

        "url": article.get(
            "url",
            "",
        ).strip(),

        "summary": article.get(
            "summary",
            "",
        ).strip(),

        "content": article.get(
            "content",
            "",
        ).strip(),

        "published": article.get(
            "published",
            "",
        ).strip(),

        "source_name": article.get(
            "source_name",
            "",
        ).strip(),

        "source_url": article.get(
            "source_url",
            "",
        ).strip(),

        "province": detect_province(article),

        "categories": categories,

        "crowd_expected": detect_crowd(article),

        "high_priority": detect_high_priority(article),

        "event_intent": detect_event_intent(article),

        "priority_score": calculate_priority_score(
            article
        ),

        "priority": detect_priority(article),
    }


# ============================================================
# 23. PARSE TOÀN BỘ ARTICLES
# ============================================================

def parse_articles(
    articles: list[dict],
) -> list[dict]:

    results = []

    for article in articles:

        if not is_event_article(article):
            continue

        normalized = normalize_article(article)

        results.append(normalized)

    results.sort(
        key=lambda item: (
            item["priority_score"],
            item["published"],
        ),
        reverse=True,
    )

    return results