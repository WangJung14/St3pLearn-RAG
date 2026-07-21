# Hàm đọc file (PDF/Text) và băm nhỏ (Chunking)
from fastapi import UploadFile

async def process_and_store_document(file: UploadFile, course_id: str) -> int:
    """
    Xử lý file tài liệu: Đọc file, băm nhỏ (chunking),
    nhúng (embedding) và lưu vào Vector DB.
    """
    print(f"[Service] Đang xử lý file {file.filename} cho khóa {course_id}...")

    # TODO: Logic RAG Ingestion sẽ viết ở đây

    # Trả về số lượng chunk giả lập
    return 15