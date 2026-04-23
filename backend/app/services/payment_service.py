"""Stripe 支付业务逻辑（兼容 one_time / recurring 价格）"""
import os
import hashlib
import logging
from datetime import datetime, timedelta, timezone

import stripe
from stripe import SignatureVerificationError

from app.database import (
    update_user,
    get_user_by_stripe_customer,
    is_event_processed,
    mark_event_processed,
)

logger = logging.getLogger("payment_service")

# ---------- 配置 ----------
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
# 一次性付款的会员有效天数（30 天）
ONETIME_MEMBERSHIP_DAYS = 30

# 初始化 Stripe
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# 缓存价格类型，避免每次创建 Session 都查询
_price_type_cache: str | None = None


def _get_price_type() -> str:
    """查询 Stripe Price 类型: 'one_time' 或 'recurring'"""
    global _price_type_cache
    if _price_type_cache:
        return _price_type_cache
    price = stripe.Price.retrieve(STRIPE_PRICE_ID)
    _price_type_cache = price.type  # 'one_time' or 'recurring'
    logger.info("Price %s type: %s", STRIPE_PRICE_ID, _price_type_cache)
    return _price_type_cache


def _idempotency_key(user_id: int, action: str, mode: str = "") -> str:
    """生成幂等键（按小时粒度，包含模式，防止短时间重复创建）"""
    now = datetime.now(timezone.utc).strftime("%Y%m%d%H")
    raw = f"{user_id}:{action}:{mode}:{now}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


# =====================================================================
# Checkout Session
# =====================================================================

async def create_checkout_session(user: dict) -> str:
    """
    创建 Stripe Checkout Session。
    自动检测 Price 类型：
    - recurring → subscription 模式
    - one_time  → payment 模式
    返回 Checkout URL。
    """
    if not STRIPE_SECRET_KEY:
        raise ValueError("未配置 STRIPE_SECRET_KEY，无法创建支付会话")
    if not STRIPE_PRICE_ID:
        raise ValueError("未配置 STRIPE_PRICE_ID，请先在 Stripe Dashboard 创建价格")

    customer_id = user.get("stripe_customer_id")

    # 首次支付：创建 Stripe Customer
    if not customer_id:
        customer = stripe.Customer.create(
            email=user["email"],
            metadata={"saveany_user_id": str(user["id"])},
        )
        customer_id = customer.id
        await update_user(user["id"], stripe_customer_id=customer_id)

    # 根据价格类型选择模式
    price_type = _get_price_type()
    mode = "subscription" if price_type == "recurring" else "payment"

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode=mode,
        line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
        success_url=f"{FRONTEND_URL}?payment=success&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{FRONTEND_URL}?payment=canceled",
        metadata={"saveany_user_id": str(user["id"])},
        idempotency_key=_idempotency_key(user["id"], "checkout", mode),
    )

    logger.info("Checkout session created: mode=%s, user=%s", mode, user["id"])
    return session.url


# =====================================================================
# Customer Portal（订阅管理，仅 subscription 模式可用）
# =====================================================================

async def verify_checkout_session(session_id: str, user: dict) -> dict:
    """
    主动验证 Stripe Checkout Session 的支付状态。
    用于支付成功跳转回来后，前端主动确认并激活会员。
    这是 webhook 的补充机制，确保即使 webhook 未到达也能激活会员。
    """
    if not STRIPE_SECRET_KEY:
        raise ValueError("未配置 STRIPE_SECRET_KEY")

    session = stripe.checkout.Session.retrieve(session_id)

    if session.payment_status != "paid":
        return {"activated": False, "reason": "支付未完成"}

    # 验证 session 属于当前用户（安全校验）
    session_user_id = _safe_metadata_get(session.metadata, "saveany_user_id")

    if session_user_id and str(user["id"]) != session_user_id:
        raise ValueError("支付会话不属于当前用户")

    # 检查用户是否已经是会员（避免重复处理）
    if user.get("subscription_status") == "active":
        return {"activated": True, "reason": "已是会员"}

    # 激活会员
    mode = session.mode or "payment"
    subscription_id = session.subscription
    customer_id = session.customer

    if mode == "subscription" and subscription_id:
        sub = stripe.Subscription.retrieve(subscription_id)
        end_date = datetime.fromtimestamp(
            sub.current_period_end, tz=timezone.utc
        ).isoformat()
        await update_user(
            user["id"],
            subscription_status="active",
            subscription_id=subscription_id,
            subscription_end_date=end_date,
            stripe_customer_id=customer_id,
        )
    else:
        end_date = (
            datetime.now(timezone.utc) + timedelta(days=ONETIME_MEMBERSHIP_DAYS)
        ).isoformat()
        payment_intent_id = session.payment_intent or ""
        await update_user(
            user["id"],
            subscription_status="active",
            subscription_id=payment_intent_id,
            subscription_end_date=end_date,
            stripe_customer_id=customer_id,
        )

    logger.info("User %s activated via verify-session (mode=%s)", user["id"], mode)
    return {"activated": True, "reason": "会员已激活"}


async def create_portal_session(user: dict) -> str:
    """创建 Stripe 客户门户会话（管理订阅/取消）"""
    if not STRIPE_SECRET_KEY:
        raise ValueError("未配置 STRIPE_SECRET_KEY")

    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        raise ValueError("您还未创建过订阅")

    portal_session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{FRONTEND_URL}?from=portal",
    )
    return portal_session.url


# =====================================================================
# Webhook 处理
# =====================================================================

async def handle_webhook_event(payload: bytes, sig_header: str) -> str:
    """处理 Stripe Webhook 事件（签名验证 + 幂等性去重）"""
    if not STRIPE_WEBHOOK_SECRET:
        raise ValueError("未配置 STRIPE_WEBHOOK_SECRET")

    # 验证签名（Stripe v15: SignatureVerificationError 在顶层）
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise ValueError("Invalid payload")
    except SignatureVerificationError:
        raise ValueError("Invalid signature")

    event_id = event.id or ""
    event_type = event.type or ""
    logger.info("Webhook event: %s (%s)", event_type, event_id)

    # 幂等性：检查是否已处理
    if await is_event_processed(event_id):
        logger.info("Event %s already processed, skipping", event_id)
        return f"Event {event_id} already processed"

    # 事件分发
    try:
        data_object = event.data.object
        if event_type == "checkout.session.completed":
            await _handle_checkout_completed(data_object)
        elif event_type == "customer.subscription.updated":
            await _handle_subscription_updated(data_object)
        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(data_object)
        elif event_type == "invoice.payment_failed":
            await _handle_payment_failed(data_object)
        else:
            logger.info("Unhandled event type: %s", event_type)

        await mark_event_processed(event_id)
        return f"Processed {event_type}"
    except Exception as e:
        logger.error("Error handling %s: %s", event_type, e)
        raise


# ---------------------------------------------------------------------------
# 各事件处理器
# ---------------------------------------------------------------------------

async def _handle_checkout_completed(session):
    """
    处理支付完成事件 — 激活会员。
    兼容 payment（一次性）和 subscription（订阅）两种模式。
    session 可能是 Stripe 对象或 dict（来自 webhook construct_event）。
    """
    customer_id = _safe_get(session, "customer")
    if not customer_id:
        logger.warning("checkout.session.completed without customer")
        return

    user = await _find_user_from_session(session)
    if not user:
        logger.warning("No user found for customer %s", customer_id)
        return

    subscription_id = _safe_get(session, "subscription")
    mode = _safe_get(session, "mode") or "payment"

    if mode == "subscription" and subscription_id:
        # 订阅模式：从 Subscription 对象获取到期日
        sub = stripe.Subscription.retrieve(subscription_id)
        end_date = datetime.fromtimestamp(
            sub.current_period_end, tz=timezone.utc
        ).isoformat()
        await update_user(
            user["id"],
            subscription_status="active",
            subscription_id=subscription_id,
            subscription_end_date=end_date,
            stripe_customer_id=customer_id,
        )
        logger.info("User %s activated subscription until %s", user["id"], end_date)
    else:
        # 一次性付款模式：会员有效期 30 天
        end_date = (
            datetime.now(timezone.utc) + timedelta(days=ONETIME_MEMBERSHIP_DAYS)
        ).isoformat()
        payment_intent_id = _safe_get(session, "payment_intent") or ""
        await update_user(
            user["id"],
            subscription_status="active",
            subscription_id=payment_intent_id,
            subscription_end_date=end_date,
            stripe_customer_id=customer_id,
        )
        logger.info(
            "User %s activated one-time membership for %d days until %s",
            user["id"], ONETIME_MEMBERSHIP_DAYS, end_date,
        )


async def _find_user_from_session(session):
    """从 Checkout Session 中查找用户（先按 customer，再按 metadata）"""
    customer_id = _safe_get(session, "customer")
    user = await get_user_by_stripe_customer(customer_id) if customer_id else None
    if not user:
        user_id = _safe_metadata_get(_safe_get(session, "metadata"), "saveany_user_id")
        if user_id:
            from app.database import get_user_by_id
            user = await get_user_by_id(int(user_id))
    return user


def _safe_get(obj, key, default=None):
    """安全地从 Stripe 对象或 dict 中获取属性（兼容 Stripe v15 StripeObject）"""
    if isinstance(obj, dict):
        return obj.get(key, default)
    # Stripe v15 对象：用 getattr 获取属性
    val = getattr(obj, key, default)
    return val if val is not None else default


def _safe_metadata_get(metadata, key, default=None):
    """安全地从 Stripe metadata 对象中获取值"""
    if metadata is None:
        return default
    if isinstance(metadata, dict):
        return metadata.get(key, default)
    # Stripe v15 StripeObject: 支持 to_dict() 或 [] 访问
    if hasattr(metadata, 'to_dict'):
        return metadata.to_dict().get(key, default)
    try:
        return metadata[key]
    except (KeyError, TypeError):
        return default


async def _handle_subscription_updated(subscription):
    """处理订阅更新事件"""
    customer_id = _safe_get(subscription, "customer")
    if not customer_id:
        return
    user = await get_user_by_stripe_customer(customer_id)
    if not user:
        return

    status = _safe_get(subscription, "status") or ""
    end_ts = _safe_get(subscription, "current_period_end")
    end_date = (
        datetime.fromtimestamp(end_ts, tz=timezone.utc).isoformat()
        if end_ts else None
    )

    status_map = {
        "active": "active", "trialing": "active",
        "past_due": "past_due",
        "canceled": "canceled", "unpaid": "canceled",
        "incomplete_expired": "canceled",
    }
    db_status = status_map.get(status, status)

    await update_user(user["id"], subscription_status=db_status, subscription_end_date=end_date)
    logger.info("User %s subscription updated: %s", user["id"], db_status)


async def _handle_subscription_deleted(subscription):
    """处理订阅取消事件 — 降级为免费"""
    customer_id = _safe_get(subscription, "customer")
    if not customer_id:
        return
    user = await get_user_by_stripe_customer(customer_id)
    if not user:
        return

    await update_user(
        user["id"],
        subscription_status="free",
        subscription_id=None,
        subscription_end_date=None,
    )
    logger.info("User %s subscription canceled, downgraded to free", user["id"])


async def _handle_payment_failed(invoice):
    """处理支付失败事件"""
    customer_id = _safe_get(invoice, "customer")
    if not customer_id:
        return
    user = await get_user_by_stripe_customer(customer_id)
    if not user:
        return

    await update_user(user["id"], subscription_status="past_due")
    logger.info("User %s payment failed, marked as past_due", user["id"])
