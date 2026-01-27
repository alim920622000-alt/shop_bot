from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from app.db.database import Database
from app.handlers_admin_shop.start import kb_admin_main
from app.handlers_admin_shop.utils import is_shop_admin

router = Router()

def kb_back_home() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главная", callback_data="a:home")]
    ])

async def _guard_admin(db: Database, user_id: int) -> bool:
    return await is_shop_admin(db, user_id)

#@router.callback_query(F.data == "a:home")
#async def home(cq: CallbackQuery, db: Database):
#    if not await _guard_admin(db, cq.from_user.id):
 #       await cq.answer("Нет доступа", show_alert=True)
  #      return
   # await cq.message.edit_text("Админ-меню магазина:", reply_markup=kb_admin_main())
    #await cq.answer()

@router.callback_query(F.data == "a:history")
async def history(cq: CallbackQuery, db: Database):
    if not await _guard_admin(db, cq.from_user.id):
        await cq.answer("Нет доступа", show_alert=True)
        return
    await cq.message.edit_text("🕓 История заказов (пока заглушка).", reply_markup=kb_back_home())
    await cq.answer()

@router.callback_query(F.data == "a:promos")
async def promos(cq: CallbackQuery, db: Database):
    if not await _guard_admin(db, cq.from_user.id):
        await cq.answer("Нет доступа", show_alert=True)
        return
    await cq.message.edit_text("🎁 Акции (пока заглушка).", reply_markup=kb_back_home())
    await cq.answer()

@router.callback_query(F.data == "a:cabinet")
async def cabinet(cq: CallbackQuery, db: Database):
    if not await _guard_admin(db, cq.from_user.id):
        await cq.answer("Нет доступа", show_alert=True)
        return
    await cq.message.edit_text(
        "👤 Кабинет магазина (пока заглушка).\n"
        "Здесь будет: телефон, адрес, описание, лого.",
        reply_markup=kb_back_home()
    )
    await cq.answer()

@router.callback_query(F.data == "a:products")
async def products(cq: CallbackQuery, db: Database):
    if not await _guard_admin(db, cq.from_user.id):
        await cq.answer("Нет доступа", show_alert=True)
        return
    await cq.message.edit_text(
        "🧺 Продукты (пока заглушка).\n"
        "Здесь будет: категории → товары → карточка → вкл/выкл.",
        reply_markup=kb_back_home()
    )
    await cq.answer()
