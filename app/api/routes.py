# Controller định nghĩa các endpoint RAG & Document Ingestion
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from app.models.schemas import ChatRequest, ChatResponse, UploadResponse, IngestDocumentRequest, IngestTaskResponse
from app.services.document_service import process_and_store_document, process_async_ingestion
from app.services.rag_service import get_answer_from_rag
from app.db.vector_store import delete_vectors_by_document_id

router = APIRouter(prefix="/api/ai", tags=["AI Core"])

@router.post("/documents/upload", response_model=UploadResponse)
async def upload_course_document(
    course_id: str = Form(...),
    file: UploadFile = File(...)
):
    if not file.filename.lower().endswith(('.pdf', '.txt', '.docx')):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file PDF, TXT và DOCX")

    chunks_count = await process_and_store_document(file, course_id)

    return UploadResponse(
        message=f"Đã xử lý file {file.filename} cho khóa {course_id}",
        total_chunks=chunks_count
    )

@router.post("/documents/ingest", response_model=IngestTaskResponse, status_code=202)
async def ingest_document_async(
    request: IngestDocumentRequest,
    background_tasks: BackgroundTasks
):
    """
    Endpoint tiếp nhận yêu cầu nạp tài liệu bất đồng bộ từ Spring Boot.
    FastAPI trả về HTTP 202 ngay và xử lý việc tải/băm/nhúng ngầm.
    """
    try:
        background_tasks.add_task(
            process_async_ingestion,
            document_id=request.document_id,
            course_id=request.course_id,
            file_url=request.file_url,
            file_type=request.file_type,
            text_content=request.text_content,
            callback_url=request.callback_url
        )

        return IngestTaskResponse(
            message="Yêu cầu nạp tài liệu đã được tiếp nhận và xử lý ngầm.",
            document_id=request.document_id,
            status="PROCESSING"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Lỗi FastAPI: {str(e)}")

@router.delete("/documents/{document_id}")
async def delete_document_vectors(document_id: str):
    """
    Xóa toàn bộ vector thuộc document_id khỏi ChromaDB
    """
    delete_vectors_by_document_id(document_id)
    return {"message": f"Đã xóa vector cho document_id: {document_id}"}

@router.post("/chat", response_model=ChatResponse)
async def ask_course_assistant(request: ChatRequest):
    answer, sources = await get_answer_from_rag(request.question, request.course_id)
    return ChatResponse(answer=answer, source_chunks=sources)