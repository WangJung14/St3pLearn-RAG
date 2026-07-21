import json
import httpx
from typing import AsyncGenerator, List, Tuple
from app.db.vector_store import query_relevant_chunks
from app.core.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from app.models.schemas import Message

async def get_answer_from_rag(question: str, course_id: str) -> Tuple[str, List[str]]:
    """
    Hàm đồng bộ (giữ lại để tương thích ngược nếu cần).
    """
    print(f"[RAG] Đang tìm câu trả lời cho khóa {course_id}, câu hỏi: '{question}'")
    sources = query_relevant_chunks(question, course_id, top_k=3)
    if not sources:
        return (
            "Hiện tại chưa có tài liệu nào thuộc khóa học này được duyệt vào bộ nhớ AI để trả lời câu hỏi của bạn.",
            []
        )
    context_text = "\n\n".join([f"- {src}" for src in sources])
    answer = f"Dựa trên tài liệu khóa học đã được phê duyệt:\n\n{context_text}"
    return answer, sources

async def generate_rag_stream(
    question: str,
    course_id: str,
    history: List[Message]
) -> AsyncGenerator[str, None]:
    """
    Generator tạo stream phản hồi từ mô hình LLM (Ollama) dựa vào tri thức RAG và lịch sử hội thoại.
    """
    # 1. Truy vấn tài liệu liên quan
    sources = query_relevant_chunks(question, course_id, top_k=4)

    if not sources:
        yield "Hiện tại chưa có tài liệu nào thuộc khóa học này được duyệt vào bộ nhớ AI để trả lời câu hỏi của bạn."
        return

    # 2. Xây dựng Ngữ cảnh & System Prompt nghiêm ngặt
    context_text = "\n\n".join([f"[Tài liệu {i+1}]: {src}" for i, src in enumerate(sources)])

    system_prompt = (
        "Bạn là một Gia sư ảo học thuật chuyên nghiệp đại diện cho khóa học này.\n"
        "Nhiệm vụ của bạn là giải thích, phản biện và hướng dẫn học viên dựa TRÊN DUY NHẤT các đoạn ngữ cảnh (Context) được cung cấp dưới đây.\n\n"
        "CÁC LUẬT CHƠI BẮT BUỘC:\n"
        "1. Chỉ trả lời dựa trên thông tin có sẵn trong Ngữ cảnh (Context) bên dưới.\n"
        "2. Tuyệt đối KHÔNG sử dụng bất kỳ kiến thức bên ngoài nào không có trong Ngữ cảnh.\n"
        "3. Nếu thông tin trong Ngữ cảnh không đủ hoặc không có câu trả lời cho câu hỏi của học sinh, bạn BẮT BUỘC phải từ chối trả lời bằng cách nói chính xác câu sau: \"Tôi xin lỗi, câu hỏi này nằm ngoài phạm vi tài liệu kiến thức được cung cấp của khóa học.\"\n"
        "4. Tuyệt đối không tự bịa ra thông tin, không giả định và không bổ sung chi tiết ngoài tài liệu (Chống ảo giác).\n\n"
        f"Ngữ cảnh (Context):\n{context_text}"
    )

    # 3. Chuẩn bị danh sách Messages cho Ollama
    messages = [{"role": "system", "content": system_prompt}]
    
    # Nạp lịch sử hội thoại trước đó
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
        
    # Thêm câu hỏi hiện tại
    messages.append({"role": "user", "content": question})

    # 4. Gửi stream request tới Ollama
    try:
        url = f"{OLLAMA_BASE_URL}/api/chat"
        payload = {
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": True
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    yield f"Lỗi kết nối Ollama (HTTP {response.status_code})"
                    return

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        token = data.get("message", {}).get("content", "")
                        if token:
                            yield token
                    except Exception:
                        pass
    except Exception as e:
        import traceback
        print(f"[RAG_STREAM_ERROR] Lỗi khi gọi hoặc truyền stream từ Ollama: {e}")
        traceback.print_exc()
        yield f"Lỗi hệ thống khi gọi Ollama: {str(e)}"