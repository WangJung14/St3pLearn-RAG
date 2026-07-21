# (Orchestrator) Kết hợp các bước của RAG
from typing import Tuple, List

async def get_answer_from_rag(question: str, course_id: str) -> Tuple[str, List[str]]:
    """
    Xử lý câu hỏi: Query Vector DB lấy context theo course_id,
    sau đó gửi prompt cho LLM để lấy câu trả lời.
    """
    print(f"[Service] Đang tìm câu trả lời cho khóa {course_id}, câu hỏi: {question}")

    # TODO: Logic RAG Retrieval & Generation sẽ viết ở đây
    mock_answer = "Đây là câu trả lời được xử lý từ tầng Service."
    mock_sources = ["Đoạn tài liệu 1", "Đoạn tài liệu 2"]

    return mock_answer, mock_sources