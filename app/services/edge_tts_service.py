import base64
import edge_tts

async def text_to_speech_base64(text: str, voice: str = "en-US-BrianNeural") -> str:
    """
    Chuyển văn bản thành giọng nói (TTS) tiếng Anh dạng chuỗi Base64 sử dụng edge-tts.
    Giọng đọc mặc định: en-US-BrianNeural (giọng nam ấm áp, tự nhiên).
    """
    try:
        communicate = edge_tts.Communicate(text, voice)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
                
        if not audio_data:
            raise Exception("Không tạo được dữ liệu audio từ edge-tts.")
            
        return base64.b64encode(audio_data).decode("utf-8")
    except Exception as e:
        print(f"[EdgeTTS] Lỗi chuyển giọng nói: {e}")
        raise e
