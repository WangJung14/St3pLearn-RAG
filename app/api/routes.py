# controller định nghĩa các endpoint
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.models.schemas import ChatRequest, ChatResponse, UploadResponse
from app.services.document_service import process_and_store_document
from app.services.rag_service import get_answer_from_rag

# router này đóng vai trò y hệt @RestController bên Spring Boot
router = APIRouter(prefix="/api/ai", tags=["AI Core"])


@router.post("/documents/upload", response_model=UploadResponse)
async def upload_course_document(
        course_id: str = Form(...),
        file: UploadFile = File(...)
):
    if not file.filename.endswith(('.pdf', '.txt')):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file PDF và TXT")

    # Ủy quyền cho tầng Service
    chunks_count = await process_and_store_document(file, course_id)

    return UploadResponse(
        message=f"Đã xử lý file {file.filename} cho khóa {course_id}",
        total_chunks=chunks_count
    )


@router.post("/chat", response_model=ChatResponse)
async def ask_course_assistant(request: ChatRequest):
    # Ủy quyền cho tầng Service
    answer, sources = await get_answer_from_rag(request.question, request.course_id)

    return ChatResponse(answer=answer, source_chunks=sources)