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
            await connection.commit()
