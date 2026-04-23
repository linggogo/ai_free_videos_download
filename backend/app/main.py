from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import video
from app.routers import auth as auth_router
from app.routers import payment as payment_router
from app.database import init_db

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
app.include_router(auth_router.router, prefix="/api/auth")
app.include_router(payment_router.router, prefix="/api")


@app.on_event("startup")
async def startup():
    """应用启动时初始化数据库"""
    await init_db()


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "万能视频下载服务运行中"}


@app.get("/health")
async def health():
    return {"status": "ok"}
