"""Stripe 支付 API + Webhook"""
import os
import logging

from fastapi import APIRouter, HTTPException, Request, Depends

from app.auth import require_user
from app.services.payment_service import (
    create_checkout_session,
    create_portal_session,
    handle_webhook_event,
    verify_checkout_session,
)

logger = logging.getLogger("payment_router")

router = APIRouter()


@router.post("/payment/create-checkout-session")
async def api_create_checkout_session(user: dict = Depends(require_user)):
    """创建 Stripe Checkout Session，需要登录"""
    # 已是活跃会员不允许重复订阅
    if user.get("subscription_status") == "active":
        raise HTTPException(status_code=400, detail="您已是会员，无需重复购买")

    try:
        checkout_url = await create_checkout_session(user)
        return {"checkout_url": checkout_url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Create checkout session error: %s", e)
        raise HTTPException(status_code=500, detail="创建支付会话失败，请稍后重试")


@router.post("/payment/create-portal-session")
async def api_create_portal_session(user: dict = Depends(require_user)):
    """创建 Stripe 客户门户（管理订阅）"""
    try:
        portal_url = await create_portal_session(user)
        return {"portal_url": portal_url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Create portal session error: %s", e)
        raise HTTPException(status_code=500, detail="创建门户会话失败，请稍后重试")


@router.post("/payment/verify-session")
async def api_verify_session(request: Request, user: dict = Depends(require_user)):
    """
    主动验证支付结果并激活会员。
    前端支付成功跳转回来后调用此接口，确保即使 webhook 未送达也能激活。
    """
    body = await request.json()
    session_id = body.get("session_id", "")
    if not session_id:
        raise HTTPException(status_code=400, detail="缺少 session_id")

    try:
        result = await verify_checkout_session(session_id, user)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Verify session error: %s", e)
        raise HTTPException(status_code=500, detail="验证支付状态失败")


@router.post("/stripe/webhook")
async def api_stripe_webhook(request: Request):
    """
    Stripe Webhook 接收端点。
    注意：这个端点必须接收原始 body（不能被 JSON 解析），
    因为 Stripe 签名验证需要原始 payload。
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    try:
        result = await handle_webhook_event(payload, sig_header)
        return {"status": "ok", "message": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Webhook error: %s", e)
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.get("/payment/config")
async def api_payment_config():
    """返回前端需要的 Stripe 公钥和价格信息"""
    publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    return {
        "publishable_key": publishable_key,
        "price": "19.9",
        "currency": "CNY",
        "period": "月",
    }
