from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from typing import Callable, Awaitable, Any
from app.config import Settings
from app.db import Database

class AuthMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings, db: Database):
        self.settings = settings
        self.db = db

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any]
    ) -> Any:
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id is None:
            return await handler(event, data)

        if user_id in self.settings.superadmin_ids:
            role = "superadmin"
        elif user_id in self.settings.admin_ids:
            role = "admin"
        else:
            role = "none"

        await self.db.upsert_user(user_id, role)

        data["auth_user_id"] = user_id
        data["auth_role"] = role
        return await handler(event, data)
