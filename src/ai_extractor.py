import json
import logging
import re
from datetime import datetime
from typing import Dict, Optional
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from src.config import GEMINI_API_KEY

logger = logging.getLogger("ai_extractor")

# Schema định nghĩa cấu trúc dữ liệu trả về từ Gemini API
class EventExtractionSchema(BaseModel):
    is_event: bool = Field(
        description=(
            "True nếu đây là THÔNG BÁO TỔ CHỨC LỄ HỘI, SỰ KIỆN, CONCERT, ĐÊM"
            " NHẠC, TRIỂN LÃM thực sự diễn ra tại Miền Nam. False nếu là tin"
            " đời tư, phỏng vấn nghệ sĩ, scandal, sự cố thời tiết/tai nạn,"
            " đánh giá cá nhân hoặc bài báo tổng kết quá khứ."
        )
    )
    title: str = Field(
        description=(
            "Tên chính thức hoặc chủ đề của sự kiện ngắn gọn, rõ ràng (ví dụ:"
            " Concert See The Light - Day 2, Lễ hội Bánh dân gian Nam Bộ,...)"
        )
    )
    province: str = Field(
        description=(
            "Tỉnh hoặc Thành phố trực thuộc Trung ương thuộc khu vực Miền Nam"
            " Việt Nam nơi diễn ra sự kiện (VD: TPHCM, Cần Thơ, Tây Ninh, An"
            " Giang, Cà Mau, Bà Rịa - Vũng Tàu,...)"
        )
    )
    event_date: str = Field(
        description=(
            "Ngày/Tháng diễn ra sự kiện hiển thị ngắn gọn dạng DD/MM hoặc"
            " DD–DD/MM (VD: 21/11, 15–18/10). Nếu không có ngày cụ thể, trả về"
            " 'NULL'."
        )
    )
    raw_date: str = Field(
        description=(
            "Mốc ngày bắt đầu sự kiện theo chuẩn YYYY-MM-DD để lưu CSDL (VD:"
            " 2026-11-21). Nếu chỉ biết tháng/năm hoặc không rõ ngày, trả về"
            " 'NULL'."
        )
    )
    location: str = Field(
        description=(
            "Địa điểm chi tiết tổ chức sự kiện. Ưu tiên bóc tách tên công trình"
            " cụ thể (Khu đô thị Vạn Phúc, Sân vận động Thống Nhất, Công viên"
            " Sông Hậu, Nhà hát Bến Thành,...) kèm Quận/Huyện/Xã/Phường. Nếu bài"
            " báo không ghi chi tiết địa danh, trả về 'Khu vực trung tâm' + tên"
            " tỉnh."
        )
    )
    scale: str = Field(
        description=(
            "Quy mô và tính chất sự kiện. Bóc tách số lượng người dự kiến (VD:"
            " ~20.000 người), hoặc các đặc điểm nổi bật như 'có bắn pháo hoa',"
            " 'đại nhạc hội / concert', 'quy mô cấp tỉnh/quốc gia'."
        )
    )
    priority: str = Field(
        description=(
            "Đánh giá mức độ ưu tiên theo quy mô: Trả về 'CAO' nếu sự kiện có"
            " quy mô từ 10.000 người trở lên, hoặc có bắn pháo hoa, hoặc là đại"
            " nhạc hội/concert hoành tráng; trả về 'TB' cho các sự kiện còn"
            " lại."
        )
    )
    summary: str = Field(
        description=(
            "Tóm tắt ngắn gọn nội dung và ý nghĩa của sự kiện trong 1–2 câu"
            " súc tích."
        )
    )

def extract_event_with_ai(article_title: str, article_text: str) -> Optional[Dict]:
    """Sử dụng Google Gemini API (model gemini-2.5-flash) để phân tích, tóm tắt và trích xuất thông tin sự kiện."""
    if not GEMINI_API_KEY:
        logger.warning("Chưa cấu hình GEMINI_API_KEY, bỏ qua trích xuất bằng AI.")
        return None

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"""
Bạn là chuyên gia phân tích dữ liệu sự kiện văn hóa, giải trí tại miền Nam Việt Nam. 
Hôm nay là ngày 05/10/2026. Hãy phân tích kỹ bài báo dưới đây và trích xuất thông tin sự kiện chính xác dưới dạng JSON.

--- TIÊU ĐỀ BÀI BÁO ---
{article_title}

--- NỘI DUNG BÀI BÁO ---
{article_text}

--- CÁC QUY TẮC BẮT BUỘC KHI TRÍCH XUẤT ---
1. XÁC ĐỊNH BẢN CHẤT SỰ KIỆN (is_event):
- Đặt `is_event = true` NẾU VÀ CHỈ NẾU bài viết công bố/thông báo một sự kiện, lễ hội, concert, đêm nhạc, giải chạy, triển lãm SẮP HOẶC ĐANG DIỄN RA (từ hôm nay 05/10/2026 trở về sau hoặc đang diễn ra).
- Đặt `is_event = false` nếu bài viết thuộc các dạng: phỏng vấn nghệ sĩ, đời tư cá nhân, tin đồn, sự cố thiên tai/tai nạn, hoặc bài viết review/nhìn lại sự kiện đã kết thúc trong quá khứ.

2. TRÍCH XUẤT NGHÊM NGẶT VỀ NGÀY GIỜ (event_date, raw_date):
- Quét kỹ từng mốc ngày được đề cập trong bài.
- `event_date`: Trả về dạng DD/MM (VD: '21/11') hoặc DD–DD/MM (VD: '15–18/10'). Nếu không rõ, trả về 'NULL'.
- `raw_date`: BẮT BUỘC trả về định dạng chuẩn ISO `YYYY-MM-DD` (Giả định năm 2026 nếu bài báo không ghi năm, VD: '2026-11-21'). Nếu không xác định được ngày cụ thể, trả về 'NULL'.

3. TRÍCH XUẤT ĐỊA ĐIỂM (location, province):
- `province`: Tên Tỉnh/Thành phố thuộc Miền Nam (VD: TPHCM, Cần Thơ, An Giang, Tây Ninh, Vĩnh Long,...).
- `location`: Bóc tách địa danh cụ thể tổ chức sự kiện. Nếu không có, trả về "Khu vực trung tâm (<Tên Tỉnh/Thành>)".

4. QUY MÔ VÀ ĐÁNH GIÁ ƯU TIÊN (scale, priority):
- `scale`: Thông tin quy mô hoặc số lượng người tham dự.
- `priority`: Trả về 'CAO' nếu dự kiến từ 10.000 người trở lên HOẶC có bắn pháo hoa HOẶC concert lớn. Còn lại trả về 'TB'.
"""

        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=EventExtractionSchema,
                temperature=0.1,
            ),
        )

        data = json.loads(response.text)

        # Nếu AI xác định đây không phải là bài báo thông báo sự kiện -> Bỏ qua
        if not data.get("is_event"):
            return None

        # ------------------------------------------------------------------
        # XỬ LÝ CHỐNG LỖI NULL: Tự động gán ngày mặc định nếu bài báo thiếu ngày
        # ------------------------------------------------------------------
        today_iso = datetime.now().strftime("%Y-%m-%d")
        today_display = datetime.now().strftime("%d/%m")

        raw_d = data.get("raw_date", "NULL")
        if not raw_d or raw_d == "NULL" or not re.match(r"^\d{4}-\d{2}-\d{2}$", raw_d):
            data["raw_date"] = today_iso

        event_d = data.get("event_date", "NULL")
        if not event_d or event_d == "NULL":
            data["event_date"] = today_display

        return data

    except Exception as e:
        logger.error(f"Lỗi khi gọi Gemini API trích xuất sự kiện: {e}")
        return None