import json
import httpx
from app.core.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from app.models.schemas import GenerateQuizResponse, GenerateFlashcardResponse

def truncate_text(text: str, max_chars: int = 3000) -> str:
    """
    Cắt ngắn văn bản để tránh quá tải cho mô hình LLM nhỏ
    """
    if len(text) > max_chars:
        return text[:max_chars] + "... [Văn bản bị cắt ngắn do độ dài quá giới hạn]"
    return text

async def generate_quiz_from_text(
    text: str,
    num_questions: int = 5,
    question_type: str = "SINGLE_CHOICE",
    existing_questions: list = None
) -> GenerateQuizResponse:
    """
    Tạo danh sách câu hỏi trắc nghiệm từ văn bản đầu vào dùng Ollama JSON mode.
    Hỗ trợ SINGLE_CHOICE, MULTIPLE_CHOICE, TRUE_FALSE, ESSAY và chống trùng lặp.
    """
    truncated = truncate_text(text)
    existing_questions = existing_questions or []
    
    avoid_duplicates_text = ""
    if existing_questions:
        avoid_duplicates_text = (
            "YÊU CẦU TRÁNH TRÙNG LẶP:\n"
            "Không được sinh ra các câu hỏi trùng hoặc có ý nghĩa tương tự với các câu hỏi sau đây:\n"
            + "\n".join(f"- {q}" for q in existing_questions) + "\n\n"
        )

    # Xây dựng chỉ dẫn loại câu hỏi
    if question_type == "MULTIPLE_CHOICE":
        type_instruction = (
            f"tạo ra đúng {num_questions} câu hỏi trắc nghiệm chọn nhiều đáp án đúng (Multiple Choice).\n"
            "YÊU CẦU BẮT BUỘC:\n"
            "1. Mỗi câu hỏi phải có đúng 4 đáp án (lần lượt gắn ID là: \"A\", \"B\", \"C\", \"D\").\n"
            "2. Phải có từ 2 đến 3 đáp án đúng (is_correct: true), các đáp án còn lại là sai (is_correct: false).\n"
            "3. Phần giải thích (explanation) phải nêu rõ lý do tại sao các đáp án đúng đó là chính xác bằng tiếng Việt.\n"
        )
        sample_json = (
            "{\n"
            "  \"questions\": [\n"
            "    {\n"
            "      \"question_text\": \"Những từ nào sau đây là danh từ?\",\n"
            "      \"options\": [\n"
            "        {\"id\": \"A\", \"text\": \"Run\", \"is_correct\": false},\n"
            "        {\"id\": \"B\", \"text\": \"Apple\", \"is_correct\": true},\n"
            "        {\"id\": \"C\", \"text\": \"Happiness\", \"is_correct\": true},\n"
            "        {\"id\": \"D\", \"text\": \"Beautiful\", \"is_correct\": false}\n"
            "      ],\n"
            "      \"explanation\": \"Apple và Happiness là danh từ. Run là động từ, Beautiful là tính từ.\"\n"
            "    }\n"
            "  ]\n"
            "}"
        )
    elif question_type == "TRUE_FALSE":
        type_instruction = (
            f"tạo ra đúng {num_questions} câu hỏi Đúng/Sai (True/False).\n"
            "YÊU CẦU BẮT BUỘC:\n"
            "1. Mỗi câu hỏi chỉ có đúng 2 đáp án (gắn ID là \"A\" và \"B\").\n"
            "2. Một đáp án có text là \"Đúng\" (True), đáp án kia là \"Sai\" (False). Chỉ có 1 đáp án có is_correct: true.\n"
            "3. Phần giải thích (explanation) giải thích ngắn gọn bằng tiếng Việt.\n"
        )
        sample_json = (
            "{\n"
            "  \"questions\": [\n"
            "    {\n"
            "      \"question_text\": \"Trái Đất quay quanh Mặt Trời.\",\n"
            "      \"options\": [\n"
            "        {\"id\": \"A\", \"text\": \"Đúng\", \"is_correct\": true},\n"
            "        {\"id\": \"B\", \"text\": \"Sai\", \"is_correct\": false}\n"
            "      ],\n"
            "      \"explanation\": \"Trái Đất thực sự quay quanh Mặt Trời theo chu kỳ khoảng 365 ngày.\"\n"
            "    }\n"
            "  ]\n"
            "}"
        )
    elif question_type == "ESSAY":
        type_instruction = (
            f"tạo ra đúng {num_questions} câu hỏi tự luận/điền từ/trả lời ngắn (Essay/Text).\n"
            "YÊU CẦU BẮT BUỘC:\n"
            "1. options để trống (mảng rỗng []).\n"
            "2. Phần giải thích (explanation) bắt buộc phải chứa nội dung câu trả lời mẫu (Sample Answer) hoặc hướng dẫn giải chi tiết bằng tiếng Việt.\n"
        )
        sample_json = (
            "{\n"
            "  \"questions\": [\n"
            "    {\n"
            "      \"question_text\": \"Hãy giải thích khái niệm của thì hiện tại hoàn thành và cho ví dụ.\",\n"
            "      \"options\": [],\n"
            "      \"explanation\": \"Câu trả lời cần nêu được cấu trúc S + have/has + V3, diễn tả hành động bắt đầu trong quá khứ kéo dài đến hiện tại. Ví dụ: I have lived here for 5 years.\"\n"
            "    }\n"
            "  ]\n"
            "}"
        )
    else: # SINGLE_CHOICE
        type_instruction = (
            f"tạo ra đúng {num_questions} câu hỏi trắc nghiệm chọn 1 đáp án đúng (Single Choice).\n"
            "YÊU CẦU BẮT BUỘC:\n"
            "1. Mỗi câu hỏi phải có đúng 4 đáp án (lần lượt gắn ID là: \"A\", \"B\", \"C\", \"D\").\n"
            "2. Chỉ có duy nhất 1 đáp án đúng (is_correct: true), 3 đáp án còn lại là sai (is_correct: false).\n"
            "3. Phần giải thích (explanation) phải nêu rõ lý do tại sao đáp án đúng đó là chính xác bằng tiếng Việt.\n"
        )
        sample_json = (
            "{\n"
            "  \"questions\": [\n"
            "    {\n"
            "      \"question_text\": \"Thì hiện tại đơn được dùng để làm gì?\",\n"
            "      \"options\": [\n"
            "        {\"id\": \"A\", \"text\": \"Diễn tả hành động đang xảy ra tại thời điểm nói\", \"is_correct\": false},\n"
            "        {\"id\": \"B\", \"text\": \"Diễn tả hành động lặp đi lặp lại hoặc thói quen\", \"is_correct\": true},\n"
            "        {\"id\": \"C\", \"text\": \"Diễn tả hành động xảy ra và kết thúc trong quá khứ\", \"is_correct\": false},\n"
            "        {\"id\": \"D\", \"text\": \"Diễn tả hành động sẽ xảy ra trong tương lai\", \"is_correct\": false}\n"
            "      ],\n"
            "      \"explanation\": \"Thì hiện tại đơn dùng để diễn tả các thói quen, hành động lặp đi lặp lại hàng ngày.\"\n"
            "    }\n"
            "  ]\n"
            "}"
        )

    prompt = (
        "Bạn là một chuyên gia khảo thí và ra đề thi chuyên nghiệp.\n"
        f"Nhiệm vụ của bạn là đọc kỹ đoạn nội dung bài học dưới đây và {type_instruction}\n"
        "Trả về đúng định dạng JSON yêu cầu. Không thêm bất cứ ký tự hay giải thích nào ngoài chuỗi JSON.\n\n"
        f"{avoid_duplicates_text}"
        f"ĐỊNH DẠNG JSON MẪU:\n{sample_json}\n\n"
        f"NỘI DUNG BÀI HỌC:\n{truncated}"
    )

    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "format": "json",
        "stream": False
    }

    last_error = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code != 200:
                    raise Exception(f"Ollama trả về HTTP {response.status_code}")
                
                result = response.json()
                response_text = result.get("response", "").strip()
                
                # Parse và validate
                json_data = json.loads(response_text)
                validated_data = GenerateQuizResponse.model_validate(json_data)
                return validated_data
        except Exception as e:
            last_error = e
            print(f"[QUIZ_GEN] Lần thử {attempt + 1} thất bại: {e}")
            
    raise Exception(f"Không thể tạo được câu hỏi hợp lệ sau 3 lần thử. Chi tiết lỗi: {last_error}")

async def generate_flashcards_from_text(text: str, num_flashcards: int = 5) -> GenerateFlashcardResponse:
    """
    Tạo danh sách thẻ flashcard học tập từ văn bản đầu vào dùng Ollama JSON mode.
    Có cơ chế tự động thử lại tối đa 3 lần.
    """
    truncated = truncate_text(text)
    
    prompt = (
        "Bạn là một gia sư hỗ trợ học tập chuyên nghiệp.\n"
        f"Nhiệm vụ của bạn là đọc kỹ đoạn nội dung bài học dưới đây và tạo ra đúng {num_flashcards} thẻ ghi nhớ học tập (Flashcards) giúp học sinh ghi nhớ từ vựng hoặc khái niệm cốt lõi.\n\n"
        "YÊU CẦU BẮT BUỘC:\n"
        "1. Mặt trước (front): Là từ vựng, thuật ngữ hoặc khái niệm chính.\n"
        "2. Mặt sau (back): Là định nghĩa, giải thích ngắn gọn hoặc nghĩa tiếng Việt tương ứng.\n"
        "3. Trả về đúng định dạng JSON yêu cầu. Không thêm bất cứ ký tự hay giải thích nào ngoài chuỗi JSON.\n\n"
        "ĐỊNH DẠNG JSON MẪU:\n"
        "{\n"
        "  \"flashcards\": [\n"
        "    {\n"
        "      \"front\": \"Present Simple\",\n"
        "      \"back\": \"Thì hiện tại đơn (dùng diễn tả thói quen, chân lý)\"\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        f"NỘI DUNG BÀI HỌC:\n{truncated}"
    )

    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "format": "json",
        "stream": False
    }

    last_error = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code != 200:
                    raise Exception(f"Ollama trả về HTTP {response.status_code}")
                
                result = response.json()
                response_text = result.get("response", "").strip()
                
                # Parse và validate
                json_data = json.loads(response_text)
                validated_data = GenerateFlashcardResponse.model_validate(json_data)
                return validated_data
        except Exception as e:
            last_error = e
            print(f"[FLASHCARD_GEN] Lần thử {attempt + 1} thất bại: {e}")
            
    raise Exception(f"Không thể tạo được flashcards hợp lệ sau 3 lần thử. Chi tiết lỗi: {last_error}")
