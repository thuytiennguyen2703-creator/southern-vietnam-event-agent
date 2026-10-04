import json
import logging
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


def extract_event_with_ai(
    article_title: str, article_text: str
) -> Optional[Dict]:
  """Sử dụng Google Gemini API (model gemini-2.5-flash) để phân tích, tóm tắt

  và trích xuất thông tin sự kiện từ các bài báo không có cấu trúc.
  """
  if not GEMINI_API_KEY:
    logger.warning("Chưa cấu hình GEMINI_API_KEY, bỏ qua trích xuất bằng AI.")
    return None

  try:
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
Bạn là chuyên gia phân tích dữ liệu sự kiện văn hóa, giải trí tại miền Nam Việt Nam.
Hãy phân tích kỹ bài báo dưới đây và trích xuất thông tin sự kiện chính xác dưới dạng JSON.

--- TIÊU ĐỀ BÀI BÁO ---
{article_title}

--- NỘI DUNG BÀI BÁO ---
{article_text}

--- CÁC QUY TẮC BẮT BUỘC KHI TRÍCH XUẤT ---
1. XÁC ĐỊNH BẢN CHẤT SỰ KIỆN (is_event):
   - Đặt `is_event = true` NẾU VÀ CHỈ NẾU bài viết công bố/thông báo một sự kiện, lễ hội, concert, đêm nhạc, giải chạy, triển lãm SẮP HOẶC ĐANG DIỄN RA.
   - Đặt `is_event = false` nếu bài viết thuộc các dạng: phỏng vấn nghệ sĩ, đời tư cá nhân, tin đồn, bài học kinh nghiệm, sự cố thiên tai/tai nạn, hoặc bài viết review/nhìn lại sự kiện đã kết thúc trong quá khứ.

2. TRÍCH XUẤT NGHÊM NGẶT VỀ NGÀY GIỜ (event_date, raw_date):
   - Quét kỹ từng mốc ngày được đề cập trong bài (kể cả trong tiêu đề lẫn nội dung).
   - Nếu bài viết đưa tin về ngày tổ chức cụ thể (VD: "diễn ra vào ngày 21/11", "từ 15 đến 18-10"):
     + `event_date`: Trả về dạng DD/MM (VD: '21/11') hoặc DD–DD/MM (VD: '15–18/10').
     + `raw_date`: Trả về định dạng ISO YYYY-MM-DD (Giả định năm hiện tại là 2026 nếu bài báo không ghi năm, VD: '2026-11-21').
   - Nếu không có ngày cụ thể mà chỉ có thông tin chung chung, đặt cả hai trường này là 'NULL'.

3. TRÍCH XUẤT ĐỊA ĐIỂM (location, province):
   - `province`: Tên Tỉnh/Thành phố thuộc Miền Nam (VD: TPHCM, Cần Thơ, An Giang, Tây Ninh, Vĩnh Long,...).
   - `location`: Bóc tách địa danh cụ thể tổ chức sự kiện (VD: "Khu đô thị Vạn Phúc", "Công viên Sông Hậu", "Nhà thi đấu Phú Thọ",...). Nếu bài viết chỉ nói chung chung tại tỉnh/thành đó mà không ghi địa điểm cụ thể, hãy trả về "Khu vực trung tâm (<Tên Tỉnh/Thành>)".

4. QUY MÔ VÀ ĐÁNH GIÁ ƯU TIÊN (scale, priority):
   - `scale`: Tìm thông tin về số lượng người tham dự (VD: "~20.000 người"), thông tin bắn pháo hoa, đại nhạc hội,...
   - `priority`: Trả về 'CAO' nếu sự kiện dự kiến từ 10.000 người trở lên HOẶC có bắn pháo hoa HOẶC là đại nhạc hội/concert quy mô lớn. Tất cả các trường hợp còn lại trả về 'TB'.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=EventExtractionSchema,
            temperature=0.1,  # Đặt nhiệt độ thấp để dữ liệu đầu ra chính xác, không sáng tạo lung tung
        ),
    )

    data = json.loads(response.text)

    # Nếu AI xác định đây không phải là bài báo thông báo sự kiện -> Bỏ qua
    if not data.get("is_event"):
      return None

    return data

  except Exception as e:
    logger.error(f"Lỗi khi gọi Gemini API trích xuất sự kiện: {e}")
    return None