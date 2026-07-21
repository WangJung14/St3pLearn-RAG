import os
import io
import httpx
from fastapi import UploadFile
import docx
import pypdf
from app.db.vector_store import delete_vectors_by_document_id, add_document_chunks

def extract_text_from_bytes(content_bytes: bytes, file_type: str) -> str:
    """
    Trích xuất văn bản thô từ mảng bytes tùy theo định dạng tệp (.docx, .pdf, .txt).
    """
    file_type = (file_type or "").lower().strip()

    if "docx" in file_type:
        doc = docx.Document(io.BytesIO(content_bytes))
        full_text = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(full_text)

    if "pdf" in file_type:
        reader = pypdf.PdfReader(io.BytesIO(content_bytes))
        extracted = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted.append(text)
        return "\n".join(extracted)

    # Đọc định dạng text mặc định
    return content_bytes.decode("utf-8", errors="ignore")

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """
    Cắt nhỏ đoạn văn bản thành các chunk nhỏ có khoảng đè (overlap).
    """
    if not text or not text.strip():
        return []

    lines = text.split("\n")
    chunks = []
    current_chunk = ""

    for line in lines:
        if len(current_chunk) + len(line) < chunk_size:
            current_chunk += line + "\n"
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            # Giữ lại khoảng đè
            current_chunk = current_chunk[-overlap:] + line + "\n" if len(current_chunk) > overlap else line + "\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks

async def process_and_store_document(file: UploadFile, course_id: str) -> int:
    """
    Xử lý file upload trực tiếp qua Multipart Form.
    """
    content_bytes = await file.read()
    file_type = file.filename.split(".")[-1] if "." in file.filename else "txt"
    text = extract_text_from_bytes(content_bytes, file_type)
    chunks = chunk_text(text)
    
    document_id = f"upload_{file.filename}"
    delete_vectors_by_document_id(document_id)
    return add_document_chunks(document_id, course_id, chunks)

async def process_async_ingestion(
    document_id: str,
    course_id: str,
    file_url: str | None,
    file_type: str | None,
    text_content: str | None,
    callback_url: str | None
):
    """
    Xử lý nạp tài liệu bất đồng bộ ngầm: Đọc từ local file / HTTP URL, băm nhỏ và lưu Vector DB.
    """
    print(f"[AsyncIngest] Bắt đầu nạp tài liệu document_id={document_id}, course_id={course_id}")
    try:
        extracted_text = ""

        if text_content and text_content.strip():
            extracted_text = text_content
        elif file_url:
            # 1. Đọc từ file local đĩa cứng
            if os.path.exists(file_url):
                with open(file_url, "rb") as f:
                    content_bytes = f.read()
                extracted_text = extract_text_from_bytes(content_bytes, file_type or file_url.split(".")[-1])
            # 2. Tải từ HTTP URL local server
            elif file_url.startswith("http://") or file_url.startswith("https://"):
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(file_url)
                    if resp.status_code == 200:
                        extracted_text = extract_text_from_bytes(resp.content, file_type or file_url.split(".")[-1])
                    else:
                        raise Exception(f"Không thể tải tệp từ {file_url}, status={resp.status_code}")

        if not extracted_text.strip():
            raise Exception("Nội dung tài liệu trống hoặc không thể trích xuất chữ.")

        # Xóa vector cũ để tránh trùng rác
        delete_vectors_by_document_id(document_id)

        # Cắt nhỏ và nhúng vào ChromaDB
        chunks = chunk_text(extracted_text)
        chunk_count = add_document_chunks(document_id, course_id, chunks)

        print(f"[AsyncIngest] Hoàn tất nạp document_id={document_id} với {chunk_count} chunks.")

        # Callback báo kết quả cho Spring Boot
        if callback_url:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.put(callback_url, json={"status": "INGESTED", "chunkCount": chunk_count})

    except Exception as e:
        print(f"[AsyncIngest] Lỗi nạp tài liệu document_id={document_id}: {e}")
        if callback_url:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.put(callback_url, json={"status": "FAILED", "error": str(e)})
            except Exception as cb_err:
                print(f"[AsyncIngest] Lỗi gửi callback: {cb_err}")