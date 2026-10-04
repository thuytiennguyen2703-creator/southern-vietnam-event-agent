import html
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from bs4 import BeautifulSoup

from src.ai_extractor import extract_event_with_ai
from src.config import EVENT_KEYWORDS, GEMINI_API_KEY, SOUTHERN_PROVINCES

logger = logging.getLogger("parser")

# Bộ từ khóa loại trừ bài báo đời tư, scandal, phỏng vấn, sự cố không phải thông báo sự kiện
EXCLUDE_KEYWORDS = [
    "nhiếp ảnh gia", "tri ân", "nguyện ước", "qua đời", "chân dung", "tâm sự", 
    "chia sẻ về", "phỏng vấn", "cuộc sống hiện tại", "nhìn lại", "đời tư", 
    "chồng tây", "vợ cũ", "hẹn hò", "chia tay", "lộ diện", "sau scandal",
    "ra sao", "ra sao sau", "bây giờ ra sao", "thay đổi thế nào", "gây chú ý", 
    "thưởng thức", "bị hoãn", "bị hủy", "nhập viện", "tai nạn", "chạy loạn", "mưa lớn"
]

# Bộ từ khóa thể hiện hành động tổ chức sự kiện
ACTION_KEYWORDS = [
    "diễn ra", "tổ chức", "khai mạc", "bế mạc", "sắp diễn ra", 
    "sắp khởi tranh", "chính thức bán vé", "sắp đổ bộ", "đăng cai", 
    "biểu diễn", "đại nhạc hội", "concert", "festival", "lễ hội", "bắn pháo hoa"
]


def clean_html(raw_html: str) -> str:
  """Loại bỏ thẻ HTML và làm sạch khoảng trắng."""
  if not raw_html:
    return ""
  soup = BeautifulSoup(raw_html, "html.parser")
  return soup.get_text(separator=" ", strip=True)


def normalize_title_for_dedup(title: str) -> str:
  """Chuẩn hóa tiêu đề để so sánh chống trùng lặp giữa nhiều báo khác nhau."""
  title_clean = title.lower()
  title_clean = re.sub(r"[\"'\(\)\[\]\-_:\.,]", " ", title_clean)
  words = [w for w in title_clean.split() if len(w) > 2]
  return " ".join(words)


def extract_province(text: str) -> Optional[str]:
  """Xác định tỉnh/thành thuộc khu vực Miền Nam."""
  text_lower = text.lower()
  for province in SOUTHERN_PROVINCES:
    if province.lower() in text_lower:
      return province
  return None


def extract_event_date_obj(text: str) -> Optional[datetime]:
  """Trích xuất mốc thời gian dạng datetime từ văn bản bằng RegEx."""
  now = datetime.now()
  current_year = now.year

  # Dạng 1: "ngày 21/11", "ngày 21 tháng 11", "ngày 21-11"
  day_exact_match = re.search(
      r"ngày\s+(\d{1,2})[\s/\-tháng\.]+(\d{1,2})(?:[\s/\-năm\.]+(\d{4}))?",
      text,
      re.IGNORECASE,
  )
  if day_exact_match:
    d, m = int(day_exact_match.group(1)), int(day_exact_match.group(2))
    y = int(day_exact_match.group(3)) if day_exact_match.group(3) else current_year
    try:
      return datetime(y, m, d)
    except ValueError:
      pass

  # Dạng 2: Khoảng ngày "15 - 18/10", "15–18/11"
  range_match = re.search(
      r"(\d{1,2})\s*[\-–—]\s*(\d{1,2})[/\s]+(?:tháng\s+)?(\d{1,2})",
      text,
      re.IGNORECASE,
  )
  if range_match:
    d1, d2, m = (
        int(range_match.group(1)),
        int(range_match.group(2)),
        int(range_match.group(3)),
    )
    y = current_year
    try:
      return datetime(y, m, d1)
    except ValueError:
      pass

  # Dạng 3: Ngày/Tháng trực tiếp (VD: 21/11/2026 hoặc 21/11)
  date_match = re.search(r"(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{4}))?", text)
  if date_match:
    d, m = int(date_match.group(1)), int(date_match.group(2))
    y = int(date_match.group(3)) if date_match.group(3) else current_year
    if 1 <= d <= 31 and 1 <= m <= 12:
      try:
        return datetime(y, m, d)
      except ValueError:
        pass

  return None


def extract_location(text: str, province: str) -> str:
  """Trích xuất địa điểm cụ thể bằng RegEx rules."""
  venue_pattern = r"((?:Khu đô thị|Sân vận động|Nhà thi đấu|Công viên|Khu du lịch|Quảng trường|Trung tâm|Cung văn hóa|Nhà hát)\s+[A-ZÀ-Ỹa-zà-ỹ0-9\s]+?(?=[.,;–\n]|$))"
  venue_match = re.search(venue_pattern, text)
  if venue_match:
    return venue_match.group(1).strip()[:50]

  admin_pattern = r"((?:Phường|Xã|Thị trấn|Quận|Huyện)\s+[A-ZÀ-Ỹa-zà-ỹ0-9\s]+?(?=[.,;–\n]|$))"
  admin_match = re.search(admin_pattern, text, re.IGNORECASE)
  if admin_match:
    return admin_match.group(1).strip()[:50]

  return f"Khu vực trung tâm ({province})"


def extract_scale(text: str) -> str:
  """Trích xuất quy mô và đặc điểm nổi bật."""
  text_lower = text.lower()
  scale_parts = []

  people_match = re.search(
      r"(\d+[\d\.,]*\s*(?:ngàn|nghìn|trăm|triệu|người))", text_lower
  )
  if people_match:
    scale_parts.append(f"~{people_match.group(1)}")
  elif any(
      k in text_lower
      for k in ["quy mô lớn", "cấp tỉnh", "quốc gia", "hoành tráng"]
  ):
    scale_parts.append("Quy mô lớn")

  if "bắn pháo hoa" in text_lower or "pháo hoa" in text_lower:
    scale_parts.append("có bắn pháo hoa")
  if (
      "đại nhạc hội" in text_lower
      or "concert" in text_lower
      or "liveshow" in text_lower
  ):
    scale_parts.append("đại nhạc hội / concert")

  return " · ".join(scale_parts) if scale_parts else ""


def parse_priority(text: str) -> str:
  """Đánh giá mức ưu tiên: CAO hoặc TB."""
  text_lower = text.lower()
  high_keywords = [
      "10.000 người",
      "bắn pháo hoa",
      "đại nhạc hội",
      "concert",
      "quy mô lớn",
      "countdown",
      "liveshow",
  ]
  if any(kw in text_lower for kw in high_keywords):
    return "CAO"
  return "TB"


def is_valid_event_article(article: Dict) -> bool:
  """Kiểm tra điều kiện tiên quyết của bài viết."""
  full_text = f"{article['title']} {clean_html(article['summary'])}"
  full_text_lower = full_text.lower()

  if any(ex in full_text_lower for ex in EXCLUDE_KEYWORDS):
    return False

  has_event_kw = any(kw.lower() in full_text_lower for kw in EVENT_KEYWORDS)
  has_action_kw = any(act.lower() in full_text_lower for act in ACTION_KEYWORDS)
  province = extract_province(full_text)

  return has_event_kw and has_action_kw and (province is not None)


def process_articles(raw_articles: List[Dict]) -> List[Dict]:
  """Lọc và bóc tách dữ liệu bài viết (Ưu tiên RegEx -> AI Gemini Fallback)."""
  processed = []
  seen_titles = set()

  for art in raw_articles:
    if not is_valid_event_article(art):
      continue

    norm_title = normalize_title_for_dedup(art["title"])

    # Khử trùng lặp nội dung giữa các trang báo khác nhau
    is_duplicate = False
    for seen in seen_titles:
      if ("mỹ tâm" in norm_title and "mỹ tâm" in seen) or (
          norm_title in seen or seen in norm_title
      ):
        is_duplicate = True
        break

    if is_duplicate:
      continue

    seen_titles.add(norm_title)

    summary_clean = clean_html(art["summary"])
    full_text = f"{art['title']} {summary_clean}"

    # 1. Thử bóc tách ngày bằng RegEx
    event_dt = extract_event_date_obj(full_text)

    event_date_str = None
    iso_date = None
    province = None
    location = None
    scale = None
    priority = None

    if event_dt:
      event_date_str = event_dt.strftime("%d/%m")
      iso_date = event_dt.strftime("%Y-%m-%d")
      province = extract_province(full_text) or "TPHCM"
      location = extract_location(full_text, province)
      scale = extract_scale(full_text)
      priority = parse_priority(full_text)

    # 2. 🤖 DÙNG AI GEMINI TRÍCH XUẤT NẾU REGEX KHÔNG BẮT ĐƯỢC NGÀY
    elif GEMINI_API_KEY:
      logger.info(f"🤖 Đang gọi AI Gemini trích xuất bài viết: {art['title']}")
      ai_data = extract_event_with_ai(art["title"], summary_clean)

      if ai_data and ai_data.get("raw_date") and ai_data.get("raw_date") != "NULL":
        event_date_str = ai_data.get("event_date")
        iso_date = ai_data.get("raw_date")
        province = ai_data.get("province", "TPHCM")
        location = ai_data.get("location", "Khu vực trung tâm")
        scale = ai_data.get("scale", "")
        priority = ai_data.get("priority", "TB")

    # Nếu cả RegEx lẫn AI đều không xác định được ngày cụ thể -> Bỏ qua bài này
    if not iso_date or iso_date == "NULL":
      continue

    event = {
        "title": art["title"],
        "link": art["link"],
        "province": province,
        "event_date": event_date_str,
        "raw_date": iso_date,
        "location": location,
        "scale": scale,
        "priority": priority,
        "source_name": art["source_name"],
        "published": art["published"],
    }
    processed.append(event)

  return processed