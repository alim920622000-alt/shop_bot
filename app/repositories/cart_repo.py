from __future__ import annotations
from typing import Sequence
from app.db.database import Database


class CartRepo:
    def __init__(self, db: Database):
        self.db = db

    async def add(self, user_id: int, product_id: int, qty: int = 1) -> None:
        async with self.db.conn() as conn:
            await conn.execute(
                """INSERT INTO cart (user_id, product_id, quantity)
                   VALUES (?, ?, ?)
                   ON CONFLICT(user_id, product_id) DO UPDATE SET quantity=quantity + excluded.quantity""",
                (user_id, product_id, qty),
            )
            await conn.commit()

    async def set_qty(self, user_id: int, product_id: int, qty: int) -> None:
        async with self.db.conn() as conn:
            if qty <= 0:
                await conn.execute(
                    "DELETE FROM cart WHERE user_id=? AND product_id=?",
                    (user_id, product_id),
                )
            else:
                await conn.execute(
                    "UPDATE cart SET quantity=? WHERE user_id=? AND product_id=?",
                    (qty, user_id, product_id),
                )
            await conn.commit()

    async def clear(self, user_id: int) -> None:
        async with self.db.conn() as conn:
            await conn.execute("DELETE FROM cart WHERE user_id=?", (user_id,))
            await conn.commit()

    async def list_items(self, user_id: int) -> Sequence[dict]:
        async with self.db.conn() as conn:
            cur = await conn.execute(
                """SELECT c.product_id, c.quantity, p.name, p.price, p.shop_id
                   FROM cart c
                   JOIN products p ON p.id = c.product_id
                   WHERE c.user_id=?
                   ORDER BY p.id DESC""",
                (user_id,),
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]
