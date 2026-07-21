# Kết nối ChromaDB, lưu trữ và xóa Vector theo document_id
import os
import chromadb
from chromadb.config import Settings

# Đường dẫn lưu DB local
CHROMA_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "chroma_db")
os.makedirs(CHROMA_DATA_PATH, exist_ok=True)

chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
collection = chroma_client.get_or_create_collection(name="course_knowledge")

def delete_vectors_by_document_id(document_id: str):
    """
    Xóa tất cả các vector thuộc document_id trước khi ingest lại để tránh nhân bản dữ liệu.
    """
    try:
        collection.delete(where={"document_id": document_id})
        print(f"[VectorStore] Đã xóa vector cũ thuộc document_id: {document_id}")
    except Exception as e:
        print(f"[VectorStore] Không thể xóa vector cũ: {e}")

def add_document_chunks(document_id: str, course_id: str, chunks: list[str]):
    """
    Thêm các đoạn chunk văn bản vào ChromaDB kèm metadata.
    """
    if not chunks:
        return 0

    ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"document_id": document_id, "course_id": course_id, "chunk_index": i} for i in range(len(chunks))]

    collection.upsert(
        documents=chunks,
        ids=ids,
        metadatas=metadatas
    )
    print(f"[VectorStore] Đã lưu {len(chunks)} chunks vào ChromaDB cho document_id: {document_id}")
    return len(chunks)

def query_relevant_chunks(question: str, course_id: str, top_k: int = 3) -> list[str]:
    """
    Truy vấn các đoạn văn bản có độ tương đồng nhất với câu hỏi.
    """
    try:
        results = collection.query(
            query_texts=[question],
            n_results=top_k,
            where={"course_id": course_id}
        )
        documents = results.get("documents", [[]])[0]
        return documents if documents else []
    except Exception as e:
        print(f"[VectorStore] Lỗi truy vấn ChromaDB: {e}")
        return []