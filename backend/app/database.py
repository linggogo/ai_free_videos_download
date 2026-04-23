"""SQLite 数据库初始化 + 用户模型 CRUD"""
import os
import aiosqlite
from pathlib import Path
from datetime import date

# 数据库文件路径
DB_PATH = Path(__file__).parent.parent / "saveany.db"

# ---------------------------------------------------------------------------
# 数据库初始化
# ---------------------------------------------------------------------------

async def init_db():
    """初始化数据库，创建表"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                stripe_customer_id TEXT,
                subscription_status TEXT DEFAULT 'free',
                subscription_id TEXT,
                subscription_end_date DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ai_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                client_ip TEXT,
                feature_type TEXT NOT NULL DEFAULT 'summarize',
                usage_date DATE NOT NULL,
                usage_count INTEGER DEFAULT 0
            )
        """)
        # 创建唯一索引（忽略 NULL 的 user_id / client_ip）
        await db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_ai_usage_user
            ON ai_usage(user_id, feature_type, usage_date) WHERE user_id IS NOT NULL
        """)
        await db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_ai_usage_ip
            ON ai_usage(client_ip, feature_type, usage_date) WHERE client_ip IS NOT NULL
        """)
        # Webhook 事件去重表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS processed_events (
                event_id TEXT PRIMARY KEY,
                processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

        # 数据库迁移：为 ai_usage 表添加 feature_type 列（如果不存在）
        try:
            await db.execute("ALTER TABLE ai_usage ADD COLUMN feature_type TEXT NOT NULL DEFAULT 'summarize'")
            await db.commit()
        except Exception:
            pass  # 列已存在，忽略错误


async def get_db():
    """获取数据库连接"""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


# ---------------------------------------------------------------------------
# 用户 CRUD
# ---------------------------------------------------------------------------

async def create_user(email: str, password_hash: str) -> dict:
    """创建用户，返回用户 dict"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, password_hash),
        )
        await db.commit()
        row = await (await db.execute(
            "SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)
        )).fetchone()
        return dict(row)


async def get_user_by_email(email: str) -> dict | None:
    """根据邮箱查找用户"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        )).fetchone()
        return dict(row) if row else None


async def get_user_by_id(user_id: int) -> dict | None:
    """根据 ID 查找用户"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        )).fetchone()
        return dict(row) if row else None


async def update_user(user_id: int, **kwargs) -> None:
    """更新用户字段"""
    if not kwargs:
        return
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE users SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            values,
        )
        await db.commit()


async def get_user_by_stripe_customer(stripe_customer_id: str) -> dict | None:
    """根据 Stripe Customer ID 查找用户"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute(
            "SELECT * FROM users WHERE stripe_customer_id = ?", (stripe_customer_id,)
        )).fetchone()
        return dict(row) if row else None


# ---------------------------------------------------------------------------
# AI 使用量 CRUD
# ---------------------------------------------------------------------------

# 免费用户每日 AI 使用次数限制
FREE_AI_DAILY_LIMIT = 3
# AI 问答每日次数限制（更高）
CHAT_AI_DAILY_LIMIT = 10


async def get_ai_usage_count(user_id: int | None, client_ip: str | None, feature_type: str = 'summarize') -> int:
    """获取今日指定 AI 功能的用户使用次数"""
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        if user_id:
            row = await (await db.execute(
                "SELECT usage_count FROM ai_usage WHERE user_id = ? AND feature_type = ? AND usage_date = ?",
                (user_id, feature_type, today),
            )).fetchone()
        else:
            row = await (await db.execute(
                "SELECT usage_count FROM ai_usage WHERE client_ip = ? AND feature_type = ? AND usage_date = ? AND user_id IS NULL",
                (client_ip, feature_type, today),
            )).fetchone()
        return row[0] if row else 0


async def increment_ai_usage(user_id: int | None, client_ip: str | None, feature_type: str = 'summarize') -> int:
    """增加 AI 使用计数，返回新计数"""
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        if user_id:
            row = await (await db.execute(
                "SELECT id FROM ai_usage WHERE user_id = ? AND feature_type = ? AND usage_date = ?",
                (user_id, feature_type, today),
            )).fetchone()
            if row:
                await db.execute(
                    "UPDATE ai_usage SET usage_count = usage_count + 1 WHERE user_id = ? AND feature_type = ? AND usage_date = ?",
                    (user_id, feature_type, today),
                )
            else:
                await db.execute(
                    "INSERT INTO ai_usage (user_id, feature_type, usage_date, usage_count) VALUES (?, ?, ?, 1)",
                    (user_id, feature_type, today),
                )
        else:
            row = await (await db.execute(
                "SELECT id FROM ai_usage WHERE client_ip = ? AND feature_type = ? AND usage_date = ? AND user_id IS NULL",
                (client_ip, feature_type, today),
            )).fetchone()
            if row:
                await db.execute(
                    "UPDATE ai_usage SET usage_count = usage_count + 1 WHERE client_ip = ? AND feature_type = ? AND usage_date = ? AND user_id IS NULL",
                    (client_ip, feature_type, today),
                )
            else:
                await db.execute(
                    "INSERT INTO ai_usage (client_ip, feature_type, usage_date, usage_count) VALUES (?, ?, ?, 1)",
                    (client_ip, feature_type, today),
                )
        await db.commit()
        return await get_ai_usage_count(user_id, client_ip, feature_type)


# ---------------------------------------------------------------------------
# Webhook 事件去重
# ---------------------------------------------------------------------------

async def is_event_processed(event_id: str) -> bool:
    """检查 webhook 事件是否已处理"""
    async with aiosqlite.connect(DB_PATH) as db:
        row = await (await db.execute(
            "SELECT 1 FROM processed_events WHERE event_id = ?", (event_id,)
        )).fetchone()
        return row is not None


async def mark_event_processed(event_id: str) -> None:
    """标记 webhook 事件为已处理"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO processed_events (event_id) VALUES (?)", (event_id,)
        )
        await db.commit()
