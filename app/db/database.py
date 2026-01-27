from __future__ import annotations

import aiosqlite
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager


@dataclass(frozen=True)
class DBConfig:
    path: str  # sqlite file path, e.g. "shop.db"


class Database:
    """
    Единая точка входа в БД: всегда включает foreign_keys и Row factory.
    """
    def __init__(self, config: DBConfig):
        self.config = config

    @asynccontextmanager
    async def conn(self) -> aiosqlite.Connection:
        connection = await aiosqlite.connect(self.config.path)
        try:
            await connection.execute("PRAGMA foreign_keys = ON;")
            connection.row_factory = aiosqlite.Row
            yield connection
        finally:
            await connection.close()

    async def init_schema(self, schema_path: Optional[str] = None) -> None:
        if schema_path is None:
            schema_path = str(Path(__file__).with_name("schema.sql"))

        sql = Path(schema_path).read_text(encoding="utf-8")
        async with self.conn() as connection:
            await connection.executescript(sql)
            # ✅ ДОБАВЬ ЭТО:
            await self._migrate(connection)

            await connection.commit()
    
    async def _migrate(self, connection: aiosqlite.Connection) -> None:
        async def has_column(table: str, col: str) -> bool:
            cur = await connection.execute(f"PRAGMA table_info({table})")
            rows = await cur.fetchall()
            return any(r["name"] == col for r in rows)

        async def add_column(table: str, col: str, ddl: str) -> None:
            if not await has_column(table, col):
                await connection.execute(f"ALTER TABLE {table} ADD COLUMN {ddl};")

        # categories: нормализованное имя для поиска/дедупликации
        await add_column("categories", "name_norm", "name_norm TEXT DEFAULT ''")

        # products: поля под поиск и импорт
        await add_column("products", "name_norm", "name_norm TEXT DEFAULT ''")
        await add_column("products", "keywords_norm", "keywords_norm TEXT DEFAULT ''")
        await add_column("products", "unit", "unit TEXT DEFAULT 'шт'")
        await add_column("products", "barcode", "barcode TEXT DEFAULT ''")
        await add_column("products", "updated_at", "updated_at DATETIME")
        await add_column("products", "local_name", "local_name TEXT DEFAULT ''")
