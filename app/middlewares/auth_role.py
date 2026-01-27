from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.db.database import Database
from app.handlers_admin_shop.utils import is_shop_admin


class ShopAuthRoleMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # ¬ data уже должен быть db: Database (у теб€ это работает, раз start_cmd получает db)
        db: Database = data["db"]

        user = getattr(event, "from_user", None)
        if user is None:
            data["auth_role"] = "none"
            return await handler(event, data)

        data["auth_role"] = "shop_admin" if await is_shop_admin(db, user.id) else "none"
        return await handler(event, data)
