# (DTO) Pydantic models định nghĩa Input/Output request

from pydantic import BaseModel, Field

# --- Schema cho API Chat (Retrieval & Generation) ---
class ChatRequest(BaseModel):
    course_id: str = Field(..., description="ID của khóa học để query đúng Vector DB")
    question: str = Field(..., description="Câu hỏi của học sinh")

class ChatResponse(BaseModel):
    answer: str = Field(..., description="Câu trả lời từ AI")
    source_chunks: list[str] = Field(default=[], description="Các đoạn text trích xuất từ tài liệu (dùng để debug hoặc hiển thị trích dẫn)")

# --- Schema cho Response Upload (Ingestion) ---
class UploadResponse(BaseModel):
    message: str
    total_chunks: int