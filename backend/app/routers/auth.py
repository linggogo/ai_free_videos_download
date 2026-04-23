"""用户注册/登录 API"""
import re
import logging

from pydantic import BaseModel, field_validator
from fastapi import APIRouter, HTTPException

from app.database import create_user, get_user_by_email, get_ai_usage_count, FREE_AI_DAILY_LIMIT
from app.auth import hash_password, verify_password, create_token, require_user

from fastapi import Depends

logger = logging.getLogger("auth_router")

router = APIRouter()

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


class RegisterRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("请输入邮箱")
        if not _EMAIL_RE.match(v):
            raise ValueError("邮箱格式不正确")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("密码长度至少 6 位")
        if len(v) > 128:
            raise ValueError("密码长度不能超过 128 位")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return v.strip().lower()


def _user_response(user: dict) -> dict:
    """构造用户响应（过滤敏感字段）"""
    return {
        "id": user["id"],
        "email": user["email"],
        "subscription_status": user["subscription_status"],
        "subscription_end_date": user["subscription_end_date"],
        "created_at": user["created_at"],
    }


@router.post("/register")
async def api_register(req: RegisterRequest):
    """邮箱密码注册"""
    existing = await get_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=400, detail="该邮箱已注册，请直接登录")

    pw_hash = hash_password(req.password)
    user = await create_user(req.email, pw_hash)
    token = create_token(user["id"], user["email"])

    return {
        "token": token,
        "user": _user_response(user),
    }


@router.post("/login")
async def api_login(req: LoginRequest):
    """邮箱密码登录"""
    user = await get_user_by_email(req.email)
    if not user:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    token = create_token(user["id"], user["email"])

    return {
        "token": token,
        "user": _user_response(user),
    }


@router.get("/me")
async def api_get_me(user: dict = Depends(require_user)):
    """获取当前用户信息"""
    # 附加今日 AI 使用量
    usage_count = await get_ai_usage_count(user["id"], None)
    is_vip = user["subscription_status"] == "active"

    return {
        "user": _user_response(user),
        "ai_usage": {
            "used": usage_count,
            "limit": None if is_vip else FREE_AI_DAILY_LIMIT,
            "is_vip": is_vip,
        },
    }
