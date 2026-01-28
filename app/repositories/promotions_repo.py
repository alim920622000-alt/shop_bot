from __future__ import annotations
from typing import Optional, Sequence

from app.db.database import Database


class PromotionsRepo:
    def __init__(self, db: Database):
        self.db = db

    async def create(self, shop_id: int, name: str, description: str = "") -> int:
        async with self.db.conn() as conn:
            cur = await conn.execute(
                "INSERT INTO promotions (shop_id, name, description) VALUES (?, ?, ?)",
                (shop_id, name, description),
            )
            await conn.commit()
            return int(cur.lastrowid)

    async def list_for_shop(self, shop_id: int) -> Sequence[dict]:
        async with self.db.conn() as conn:
            cur = await conn.execute(
                "SELECT * FROM promotions WHERE shop_id=? ORDER BY created_at DESC",
                (shop_id,),
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def get(self, promo_id: int) -> Optional[dict]:
        async with self.db.conn() as conn:
            cur = await conn.execute(
                "SELECT * FROM promotions WHERE id=?",
                (promo_id,),
            )
            row = await cur.fetchone()
            return dict(row) if row else None

    async def list_items(self, promo_id: int) -> Sequence[dict]:
        async with self.db.conn() as conn:
            cur = await conn.execute(
                """
                SELECT p.* FROM promotion_items pi
                JOIN products p ON p.id = pi.product_id
                WHERE pi.promo_id=?
                ORDER BY p.id DESC
                """,
                (promo_id,),
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def toggle_product(self, promo_id: int, product_id: int) -> bool:
        async with self.db.conn() as conn:
            cur = await conn.execute(
                "SELECT 1 FROM promotion_items WHERE promo_id=? AND product_id=?",
                (promo_id, product_id),
            )
            exists = await cur.fetchone()
            if exists:
                await conn.execute(
                    "DELETE FROM promotion_items WHERE promo_id=? AND product_id=?",
                    (promo_id, product_id),
                )
                await conn.commit()
                return False

            await conn.execute(
                "INSERT INTO promotion_items (promo_id, product_id) VALUES (?, ?)",
                (promo_id, product_id),
            )
            await conn.commit()
            return True
