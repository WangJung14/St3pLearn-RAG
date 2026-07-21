# Orchestrator kết hợp RAG Retrieval & Generation
from typing import Tuple, List
from app.db.vector_store import query_relevant_chunks

async def get_answer_from_rag(question: str, course_id: str) -> Tuple[str, List[str]]:
    """
    Xử lý câu hỏi: Query Vector DB lấy context theo course_id,
    sau đó gửi prompt cho LLM (hoặc tổng hợp câu trả lời từ context).
    """
    print(f"[RAG] Đang tìm câu trả lời cho khóa {course_id}, câu hỏi: '{question}'")

    # 1. Truy vấn Vector DB lấy các đoạn tài liệu tương quan nhất
    sources = query_relevant_chunks(question, course_id, top_k=3)

    if not sources:
        return (
            "Hiện tại chưa có tài liệu nào thuộc khóa học này được duyệt vào bộ nhớ AI để trả lời câu hỏi của bạn.",
            []
        )

    # 2. Xây dựng câu trả lời dựa trên thông tin trích xuất từ tài liệu
    context_text = "\n\n".join([f"- {src}" for src in sources])
    answer = f"Dựa trên tài liệu khóa học đã được phê duyệt:\n\n{context_text}"

    return answer, sources