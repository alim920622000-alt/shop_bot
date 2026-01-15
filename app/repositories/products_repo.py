from __future__ import annotations
from typing import Optional, Sequence
from app.db.database import Database


class ProductsRepo:
    def __init__(self, db: Database):
        self.db = db

    async def create(self, shop_id: int, category_id: int, name: str, price: float,
                     description: str | None = None, photo_url: str | None = None) -> int:
        async with self.db.conn() as conn:
            cur = await conn.execute(
                """INSERT INTO products (shop_id, category_id, name, description, price, photo_url)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (shop_id, category_id, name, description, price, photo_url),
            )
            await conn.commit()
            return int(cur.lastrowid)

    async def update(self, product_id: int, name: str | None = None, description: str | None = None,
                     price: float | None = None, is_active: bool | None = None) -> None:
        fields = []
        params = []
        if name is not None:
            fields.append("name=?"); params.append(name)
        if description is not None:
            fields.append("description=?"); params.append(description)
        if price is not None:
            fields.append("price=?"); params.append(price)
        if is_active is not None:
            fields.append("is_active=?"); params.append(1 if is_active else 0)

        if not fields:
            return

        params.append(product_id)
        q = "UPDATE products SET " + ", ".join(fields) + " WHERE id=?"

        async with self.db.conn() as conn:
            await conn.execute(q, params)
            await conn.commit()

    async def list_by_category(self, category_id: int, active_only: bool = True) -> Sequence[dict]:
        q = "SELECT * FROM products WHERE category_id=?"
        params = [category_id]
        if active_only:
            q += " AND is_active=1"
        q += " ORDER BY id DESC"

        async with self.db.conn() as conn:
            cur = await conn.execute(q, params)
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def get(self, product_id: int) -> Optional[dict]:
        async with self.db.conn() as conn:
            cur = await conn.execute("SELECT * FROM products WHERE id=?", (product_id,))
            row = await cur.fetchone()
            return dict(row) if row else None
