from __future__ import annotations
from typing import Optional, Sequence
from app.db.database import Database
from app.utils import build_keywords, normalize


class ProductsRepo:
    def __init__(self, db: Database):
        self.db = db

    async def create(self, shop_id: int, category_id: int, name: str, price: float,
                     description: str | None = None, photo_url: str | None = None) -> int:
        name_norm = normalize(name)
        keywords_norm = build_keywords(name, description)
        async with self.db.conn() as conn:
            cur = await conn.execute(
                """INSERT INTO products (shop_id, category_id, name, name_norm, keywords_norm, description, price, photo_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (shop_id, category_id, name, name_norm, keywords_norm, description, price, photo_url),
            )
            await conn.commit()
            return int(cur.lastrowid)

    async def update(self, product_id: int, name: str | None = None, description: str | None = None,
                     price: float | None = None, is_active: bool | None = None) -> None:
        fields = []
        params = []
        existing = None
        if name is not None:
            fields.append("name=?"); params.append(name)
            fields.append("name_norm=?"); params.append(normalize(name))
        if description is not None:
            fields.append("description=?"); params.append(description)
        if name is not None or description is not None:
            if existing is None:
                existing = await self.get(product_id)
            existing_name = name if name is not None else (existing["name"] if existing else "")
            existing_desc = description if description is not None else (existing.get("description") if existing else "")
            fields.append("keywords_norm=?"); params.append(build_keywords(existing_name or "", existing_desc or ""))
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
    
    async def list_by_category_any(self, shop_id: int, category_id: int) -> Sequence[dict]:
        """Список товаров категории, включая неактивные (для админки)."""
        q = "SELECT * FROM products WHERE shop_id=? AND category_id=? ORDER BY id DESC"
        async with self.db.conn() as conn:
            cur = await conn.execute(q, (shop_id, category_id))
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def toggle_active(self, shop_id: int, product_id: int) -> Optional[bool]:
        """Переключить is_active. Возвращает новое состояние или None если товара нет."""
        async with self.db.conn() as conn:
            cur = await conn.execute(
                "SELECT is_active FROM products WHERE shop_id=? AND id=?",
                (shop_id, product_id),
            )
            row = await cur.fetchone()
            if not row:
                return None

            new_val = 0 if int(row["is_active"]) == 1 else 1
            await conn.execute(
                "UPDATE products SET is_active=? WHERE shop_id=? AND id=?",
                (new_val, shop_id, product_id),
            )
            await conn.commit()
            return bool(new_val)

    async def search(self, shop_id: int, query: str, limit: int = 20, active_only: bool = True) -> Sequence[dict]:
        """Поиск товаров (это потом напрямую пойдёт в клиентский бот)."""
        q = "SELECT * FROM products WHERE shop_id=?"
        params = [shop_id]

        if active_only:
            q += " AND is_active=1"

        # пока простой LIKE по name/description (потом улучшим на name_norm/FTS)
        q += " AND (lower(name) LIKE ? OR lower(COALESCE(description,'')) LIKE ?)"
        like = f"%{query.strip().lower()}%"
        params.extend([like, like])

        q += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        async with self.db.conn() as conn:
            cur = await conn.execute(q, params)
            rows = await cur.fetchall()
            return [dict(r) for r in rows]
