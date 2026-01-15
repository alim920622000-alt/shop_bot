from app.db.database import Database


async def get_admin_shop_ids(db: Database, user_id: int) -> list[int]:
    async with db.conn() as conn:
        cur = await conn.execute(
            "SELECT shop_id FROM shop_admins WHERE user_id=?",
            (user_id,),
        )
        rows = await cur.fetchall()
        return [int(r["shop_id"]) for r in rows]


async def is_admin_for_shop(db: Database, user_id: int) -> bool:
    shop_ids = await get_admin_shop_ids(db, user_id)
    return len(shop_ids) > 0
