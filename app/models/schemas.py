# (DTO) Pydantic models định nghĩa Input/Output request

from pydantic import BaseModel, Field
from typing import Optional, List

# --- Schema cho API Chat (Retrieval & Generation) ---
class Message(BaseModel):
    role: str = Field(..., description="user hoặc assistant")
    content: str = Field(..., description="Nội dung tin nhắn")

class ChatRequest(BaseModel):
    course_id: str = Field(..., description="ID của khóa học để query đúng Vector DB")
    question: str = Field(..., description="Câu hỏi của học sinh")
    history: List[Message] = Field(default=[], description="Lịch sử các tin nhắn hội thoại trước đó")

class ChatResponse(BaseModel):
    answer: str = Field(..., description="Câu trả lời từ AI")
    source_chunks: List[str] = Field(default=[], description="Các đoạn text trích xuất từ tài liệu (dùng để debug hoặc hiển thị trích dẫn)")

# --- Schema cho Response Upload (Ingestion) ---
class UploadResponse(BaseModel):
    message: str
    total_chunks: int

# --- Schema cho Request/Response Ingest từ Spring Boot ---
class IngestDocumentRequest(BaseModel):
    document_id: str = Field(..., description="ID độc nhất của tài liệu")
    course_id: str = Field(..., description="ID của khóa học")
    file_url: Optional[str] = Field(default=None, description="URL hoặc đường dẫn tệp local")
    file_type: Optional[str] = Field(default="docx", description="Định dạng tệp: docx, pdf, txt")
    text_content: Optional[str] = Field(default=None, description="Nội dung văn bản nếu nhập trực tiếp")
    callback_url: Optional[str] = Field(default=None, description="URL callback để cập nhật kết quả cho Spring Boot")

class IngestTaskResponse(BaseModel):
    message: str
    document_id: str
    status: str = "PROCESSING"