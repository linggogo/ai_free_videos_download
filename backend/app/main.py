from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import video

app = FastAPI(
    title="万能视频下载 API",
    description="基于 yt-dlp 的万能视频下载服务",
    version="1.0.0",
)

# CORS 配置 - 允许前端开发服务器访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(video.router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "万能视频下载服务运行中"}


@app.get("/health")
async def health():
    return {"status": "ok"}
