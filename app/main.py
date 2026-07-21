# Điểm khởi chạy FastAPI application

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.api.routes import router as ai_router

app = FastAPI(
    title="St3pLearn AI Service",
    description="Microservice xử lý RAG và Machine Learning cho nền tảng E-learning",
    version="1.0.0"
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "ai-service is running!"}

# Đăng ký Controller vào App chính
app.include_router(ai_router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)