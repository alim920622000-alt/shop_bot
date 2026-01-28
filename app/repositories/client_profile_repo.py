from __future__ import annotations
from typing import Optional

from app.db.database import Database


class ClientProfileRepo:
    def __init__(self, db: Database):
        self.db = db

    async def get(self, user_id: int) -> Optional[dict]:
        async with self.db.conn() as conn:
            cur = await conn.execute(
                "SELECT * FROM client_profiles WHERE user_id=?",
                (user_id,),
            )
            row = await cur.fetchone()
            return dict(row) if row else None

    async def upsert(self, user_id: int, full_name: str, phone: str, address: str) -> None:
        async with self.db.conn() as conn:
            await conn.execute(
                """
                INSERT INTO client_profiles (user_id, full_name, phone, address, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    full_name=excluded.full_name,
                    phone=excluded.phone,
                    address=excluded.address,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (user_id, full_name, phone, address),
            )
            await conn.commit()
