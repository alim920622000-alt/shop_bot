from __future__ import annotations
from typing import Sequence

from app.db.database import Database


class ChatRepo:
    def __init__(self, db: Database):
        self.db = db

    async def add_message(self, order_id: int, sender_role: str, sender_user_id: int, message: str) -> int:
        async with self.db.conn() as conn:
            cur = await conn.execute(
                """
                INSERT INTO order_chat_messages (order_id, sender_role, sender_user_id, message)
                VALUES (?, ?, ?, ?)
                """,
                (order_id, sender_role, sender_user_id, message),
            )
            await conn.commit()
            return int(cur.lastrowid)

    async def list_messages(self, order_id: int, limit: int = 20) -> Sequence[dict]:
        async with self.db.conn() as conn:
            cur = await conn.execute(
                """
                SELECT * FROM order_chat_messages
                WHERE order_id=?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (order_id, limit),
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def list_active_orders_for_client(self, client_user_id: int) -> Sequence[dict]:
        async with self.db.conn() as conn:
            cur = await conn.execute(
                """
                SELECT DISTINCT o.*
                FROM orders o
                JOIN order_chat_messages m ON m.order_id = o.id
                WHERE o.client_user_id=?
                ORDER BY o.created_at DESC
                """,
                (client_user_id,),
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def list_active_orders_for_shop(self, shop_id: int) -> Sequence[dict]:
        async with self.db.conn() as conn:
            cur = await conn.execute(
                """
                SELECT DISTINCT o.*
                FROM orders o
                JOIN order_chat_messages m ON m.order_id = o.id
                WHERE o.shop_id=?
                ORDER BY o.created_at DESC
                """,
                (shop_id,),
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]
