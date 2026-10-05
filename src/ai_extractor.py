import json
import logging
from datetime import datetime
from typing import Dict, Optional
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from src.config import GEMINI_API_KEY

logger = logging.getLogger("ai_extractor")

class EventExtractionSchema(BaseModel):
    is_event: bool = Field(
        description=(
            "True nếu bài viết thông báo hoặc nói về sự kiện, lễ hội, concert, marathon, "
            "hội chợ, triển lãm hoặc hoạt động tập trung đông người tại các tỉnh Miền Nam. "
            "False nếu là tin đời tư, tai nạn, scandal, phỏng vấn hoặc chính trị khô khan."
        )
    )
    title: str = Field(description="Tên chính thức của sự kiện ngắn gọn, rõ ràng.")
    province: str = Field(description="Tỉnh hoặc Thành phố tại Miền Nam (VD: TP.HCM, Đồng Tháp, Cần Thơ, Tây Ninh,...).")
    event_date: str = Field(description="Ngày diễn ra định dạng DD/MM hoặc khoảng DD–DD/MM (VD: 09–11/10).")
    raw_date: str = Field(description="Ngày bắt đầu theo chuẩn YYYY-MM-DD (VD: 2026-10-09).")
    time: str = Field(description="Giờ diễn ra sự kiện cụ thể nếu có (VD: 19:00). Nếu không có, ghi 'Cả ngày' hoặc 'Đang cập nhật'.")
    location: str = Field(description="Địa điểm tổ chức cụ thể kèm phường/xã hoặc khu vực (VD: Quảng trường Văn Miếu, phường Cao Lãnh).")
    scale: str = Field(description="Quy mô sự kiện kết hợp đặc điểm nổi bật (VD: '~15.545 người · có đại nhạc hội').")
    priority: str = Field(description="BẮT BUỘC gắn 'CAO' nếu quy mô từ 10.000 người trở lên, có bắn pháo hoa hoặc đại nhạc hội/concert lớn; ngược lại ghi 'TB'.")
    priority_reason: str = Field(description="Lý do ưu tiên mạng cụ thể (VD: quy mô ~15.545 người; đại nhạc hội lớn; kéo dài 3 ngày).")
    summary: str = Field(description="Tóm tắt ngắn gọn nội dung sự kiện trong 1 câu.")

def extract_event_with_ai(article_title: str, article_text: str) -> Optional[Dict]:
    """Sử dụng Gemini API (model gemini-2.5-flash) để trích xuất thông tin sự kiện chi tiết."""
    if not GEMINI_API_KEY:
        logger.warning("Chưa cấu hình GEMINI_API_KEY, bỏ qua trích xuất bằng AI.")
        return None

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"""
Bạn là chuyên gia trích xuất tin tức sự kiện tại Miền Nam Việt Nam. Hôm nay là ngày 05/10/2026.
Hãy đọc kỹ bài báo sau và trả về thông tin dưới dạng JSON chuẩn xác nhất:

--- TIÊU ĐỀ BÀI BÁO ---
{article_title}

--- NỘI DUNG BÀI BÁO ---
{article_text}

--- QUY TẮC TRÍCH XUẤT ---
1. is_event: true nếu đây là thông báo sự kiện, lễ hội, concert, giải thể thao/marathon, hội chợ; false nếu là tin đời tư, tai nạn, review quá khứ.
2. raw_date & event_date: Trích xuất chính xác mốc ngày diễn ra (raw_date theo chuẩn YYYY-MM-DD, event_date theo dạng DD/MM hoặc DD–DD/MM).
3. time: Lấy giờ diễn ra cụ thể nếu bài báo nhắc tới (VD: 19:00).
4. scale & priority_reason: Bóc tách rõ số lượng người (VD: ~15.545 người), hoạt động đi kèm (đại nhạc hội, pháo hoa) và lý do ưu tiên mạng.
5. priority: BẮT BUỘC gắn 'CAO' nếu quy mô từ 10.000 người trở lên, có đại nhạc hội/concert lớn hoặc pháo hoa; các sự kiện còn lại gán 'TB'.
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
        if not data.get("is_event"):
            return None

        # Chống lỗi trống ngày tháng, tự động đồng bộ theo ngày hiện tại nếu thiếu
        today_iso = datetime.now().strftime("%Y-%m-%d")
        if not data.get("raw_date") or data.get("raw_date") == "NULL":
            data["raw_date"] = today_iso
            
        if not data.get("event_date") or data.get("event_date") == "NULL":
            try:
                dt_obj = datetime.strptime(data["raw_date"], "%Y-%m-%d")
                data["event_date"] = dt_obj.strftime("%d/%m")
            except:
                data["event_date"] = datetime.now().strftime("%d/%m")

        return data

    except Exception as e:
        logger.error(f"Lỗi trích xuất AI: {e}")
        return None