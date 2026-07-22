import json
import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from app.services.edge_tts_service import text_to_speech_base64

router = APIRouter(prefix="/api/ai/speaking", tags=["AI Speaking"])

# Địa chỉ endpoint của API Gateway / Spring Boot để đồng bộ dữ liệu
SPRING_BOOT_API_URL = "http://127.0.0.1:8080/api/learning/speaking/evaluations"

async def call_ollama_chat(messages: list) -> str:
    """
    Gọi Ollama Chat API để lấy câu trả lời từ mô hình
    """
    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload)
        if response.status_code != 200:
            raise Exception(f"Ollama trả về HTTP {response.status_code}")
        result = response.json()
        return result.get("message", {}).get("content", "").strip()

async def call_ollama_generate_json(prompt: str) -> dict:
    """
    Gọi Ollama Generate API ở chế độ JSON để chấm điểm/nhận xét
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "format": "json",
        "stream": False
    }
    
    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(url, json=payload)
        if response.status_code != 200:
            raise Exception(f"Ollama trả về HTTP {response.status_code}")
        
        result = response.json()
        response_text = result.get("response", "").strip()
        return json.loads(response_text)

async def send_evaluation_to_springboot(student_id: str, course_id: str, lesson_id: str, evaluation_data: dict):
    """
    Gửi kết quả nhận xét từ AI sang Spring Boot lưu PostgreSQL
    """
    payload = {
        "studentId": student_id,
        "courseId": course_id,
        "lessonId": lesson_id,
        "feedback": json.dumps(evaluation_data, ensure_ascii=False)
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"Content-Type": "application/json"}
            response = await client.post(SPRING_BOOT_API_URL, json=payload, headers=headers)
            print(f"[SpeakingSync] Sync sang Spring Boot: HTTP {response.status_code}")
    except Exception as e:
        print(f"[SpeakingSync] Không thể sync sang Spring Boot: {e}")

@router.websocket("/ws")
async def speaking_websocket_endpoint(
    websocket: WebSocket,
    studentId: str = "unknown",
    courseId: str = "unknown",
    lessonId: str = "unknown",
    topicContent: str = ""
):
    await websocket.accept()
    print(f"[SpeakingWS] Học sinh {studentId} đã kết nối phòng nói chuyện (Lesson: {lessonId})")
    
    # Lịch sử hội thoại
    system_prompt = (
        "You are a friendly, casual native English-speaking friend having a warm, informal chat with the user. "
        "Your replies must be natural, engaging, and extremely short (under 20 words). "
        "Always ask simple, open questions to keep the chat going. "
        "Never teach, lecture, correct grammar, or sound like a teacher. Just be a normal friend."
    )
    
    if topicContent and topicContent.strip():
        system_prompt += f"\nThe conversation topic, context, or vocabulary guidelines to discuss:\n{topicContent.strip()}"
        
    conversation_history = [
        {"role": "system", "content": system_prompt}
    ]
    
    try:
        # 1. AI chủ động mở lời trước
        conversation_history.append({"role": "user", "content": "Hello, let's start our conversation."})
        ai_response = await call_ollama_chat(conversation_history)
        
        # Xóa câu chào mồi của hệ thống khỏi lịch sử hiển thị
        conversation_history.pop() 
        conversation_history.append({"role": "assistant", "content": ai_response})
        
        # TTS cho lời chào
        audio_base64 = await text_to_speech_base64(ai_response)
        
        # Gửi về client
        await websocket.send_json({
            "type": "AI_RESPONSE",
            "text": ai_response,
            "audio": audio_base64
        })
        
        # 2. Vòng lặp giao tiếp
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            msg_type = message.get("type")
            
            if msg_type == "USER_SPEECH":
                user_text = message.get("text", "").strip()
                if not user_text:
                    continue
                
                print(f"[SpeakingWS] Học sinh nói: {user_text}")
                conversation_history.append({"role": "user", "content": user_text})
                
                # Gọi LLM phản hồi
                ai_reply = await call_ollama_chat(conversation_history)
                conversation_history.append({"role": "assistant", "content": ai_reply})
                
                # Gọi TTS sinh giọng nói
                audio_reply_b64 = await text_to_speech_base64(ai_reply)
                
                # Trả về cho client
                await websocket.send_json({
                    "type": "AI_RESPONSE",
                    "text": ai_reply,
                    "audio": audio_reply_b64
                })
                
            elif msg_type == "END_CALL":
                print(f"[SpeakingWS] Nhận lệnh kết thúc phiên từ học sinh {studentId}. Đang phân tích lỗi...")
                
                # Xây dựng prompt nhờ AI phân tích lỗi sai ngữ pháp
                chat_log = ""
                for msg in conversation_history:
                    if msg["role"] == "user":
                        chat_log += f"Student: {msg['content']}\n"
                    elif msg["role"] == "assistant":
                        chat_log += f"Friend: {msg['content']}\n"
                
                eval_prompt = (
                    "Bạn là chuyên gia phân tích lỗi ngữ pháp tiếng Anh. Hãy đọc kỹ lịch sử cuộc trò chuyện dưới đây của học sinh và chỉ ra các lỗi sai ngữ pháp, từ vựng hoặc diễn đạt chưa tự nhiên, kèm theo gợi ý sửa lại tốt hơn.\n\n"
                    "LỊCH SỬ CUỘC TRÒ CHUYỆN:\n"
                    f"{chat_log}\n"
                    "YÊU CẦU BẮT BUỘC:\n"
                    "1. Chỉ trả về một chuỗi JSON theo đúng định dạng mẫu dưới đây. Không thêm giải thích gì ngoài JSON.\n"
                    "2. Nhận xét chi tiết (feedback) viết bằng tiếng Việt.\n"
                    "3. Nếu học sinh nói quá ít hoặc không có lỗi sai, mảng corrections để trống.\n\n"
                    "ĐỊNH DẠNG JSON MẪU:\n"
                    "{\n"
                    "  \"feedback\": \"Bạn giao tiếp rất tự nhiên và vui vẻ, tuy nhiên hãy lưu ý cách chia động từ ở quá khứ...\",\n"
                    "  \"corrections\": [\n"
                    "    {\n"
                    "      \"original\": \"I goes to school yesterday\",\n"
                    "      \"corrected\": \"I went to school yesterday\",\n"
                    "      \"explanation\": \"Yesterday chỉ quá khứ nên động từ 'go' phải chuyển thành 'went'.\"\n"
                    "    }\n"
                    "  ]\n"
                    "}\n"
                )
                
                try:
                    eval_data = await call_ollama_generate_json(eval_prompt)
                except Exception as eval_err:
                    print(f"[SpeakingWS] Lỗi sinh JSON nhận xét: {eval_err}")
                    eval_data = {
                        "feedback": "Không thể phân tích cuộc trò chuyện này do lỗi xử lý AI.",
                        "corrections": []
                    }
                
                # Lưu vào Spring Boot DB
                await send_evaluation_to_springboot(studentId, courseId, lessonId, eval_data)
                
                # Bắn kết quả về cho client hiển thị UI
                await websocket.send_json({
                    "type": "EVALUATION",
                    "evaluation": eval_data
                })
                break
                
    except WebSocketDisconnect:
        print(f"[SpeakingWS] Học sinh {studentId} đột ngột ngắt kết nối WebSocket.")
    except Exception as e:
        print(f"[SpeakingWS] Lỗi xử lý WebSocket: {e}")
        try:
            await websocket.send_json({"type": "ERROR", "message": str(e)})
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass
