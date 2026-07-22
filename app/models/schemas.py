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

# --- Schemas cho Auto-Generate Quiz & Flashcard ---

class Option(BaseModel):
    id: str = Field(..., description="ID của đáp án, ví dụ: A, B, C, D")
    text: str = Field(..., description="Nội dung đáp án")
    is_correct: bool = Field(..., description="Đúng (true) hoặc Sai (false)")

class Question(BaseModel):
    question_text: str = Field(..., description="Nội dung câu hỏi")
    options: List[Option] = Field(default=[], description="Danh sách đáp án (nếu có)")
    explanation: str = Field(..., description="Giải thích vì sao đáp án đó đúng hoặc câu trả lời mẫu")

class GenerateQuizRequest(BaseModel):
    text: str = Field(..., description="Nội dung văn bản làm căn cứ tạo câu hỏi")
    num_questions: int = Field(default=5, description="Số lượng câu hỏi muốn tạo")
    question_type: str = Field(default="SINGLE_CHOICE", description="Loại câu hỏi muốn tạo (SINGLE_CHOICE, MULTIPLE_CHOICE, TRUE_FALSE, ESSAY)")
    existing_questions: List[str] = Field(default=[], description="Danh sách tiêu đề câu hỏi đã tồn tại để tránh trùng lặp")

class GenerateQuizResponse(BaseModel):
    questions: List[Question] = Field(..., description="Danh sách các câu hỏi trắc nghiệm")

class FlashcardItem(BaseModel):
    front: str = Field(..., description="Từ vựng hoặc khái niệm (Mặt trước)")
    back: str = Field(..., description="Định nghĩa hoặc nghĩa tiếng Việt (Mặt sau)")

class GenerateFlashcardRequest(BaseModel):
    text: str = Field(..., description="Nội dung văn bản làm căn cứ tạo flashcards")
    num_flashcards: int = Field(default=5, description="Số lượng flashcard muốn tạo")

class GenerateFlashcardResponse(BaseModel):
    flashcards: List[FlashcardItem] = Field(..., description="Danh sách các thẻ flashcard")