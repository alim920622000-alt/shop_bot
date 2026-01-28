from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.handlers_admin_restaurant.start import kb_admin_main  # добавь импорт

from app.db.database import Database
from app.handlers_admin_restaurant.utils import get_admin_restaurant_ids
from app.repositories.orders_repo import OrdersRepo
from app.repositories.chat_repo import ChatRepo

router = Router()

CURRENT = ["new", "preparing", "on_the_way"]
DONE = ["finished", "canceled"]


def kb_orders_list(order_ids: list[int]) -> InlineKeyboardMarkup:
    kb = []
    for oid in order_ids:
        kb.append([InlineKeyboardButton(text=f"Заказ #{oid}", callback_data=f"r:order:{oid}")])

    kb.append([
        InlineKeyboardButton(text="🏠 Главная", callback_data="r:home"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="r:back:main"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def kb_order_card(order_id: int) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="💬 Чат по заказу", callback_data=f"r:chat:order:{order_id}")],
        [InlineKeyboardButton(text="👨‍🍳 Готовится", callback_data=f"r:st:{order_id}:preparing")],
        [InlineKeyboardButton(text="🚚 В пути", callback_data=f"r:st:{order_id}:on_the_way")],
        [InlineKeyboardButton(text="✅ Завершён", callback_data=f"r:st:{order_id}:finished")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"r:st:{order_id}:canceled")],
        [
            InlineKeyboardButton(text="🏠 Главная", callback_data="r:home"),
            InlineKeyboardButton(text="🔙 Назад", callback_data="r:orders"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


class ChatStates(StatesGroup):
    chat = State()


def kb_chat_list(order_ids: list[int]) -> InlineKeyboardMarkup:
    kb = []
    for oid in order_ids:
        kb.append([InlineKeyboardButton(text=f"Чат по заказу #{oid}", callback_data=f"r:chat:open:{oid}")])
    kb.append([InlineKeyboardButton(text="🏠 Главная", callback_data="r:home")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def kb_chat_order() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="r:chat")],
        [InlineKeyboardButton(text="🏠 Главная", callback_data="r:home")],
    ])


async def render_order_card(cq: CallbackQuery, db: Database, order_id: int):
    orders = OrdersRepo(db)
    o = await orders.get_order(order_id)
    if not o:
        await cq.message.edit_text(
            "Заказ не найден.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🏠 Главная", callback_data="r:home"),
                    InlineKeyboardButton(text="🔙 Назад", callback_data="r:orders"),
                ]
            ])
        )
        return

    items = await orders.get_order_items(order_id)
    lines = [
        f"Заказ #{o['id']}",
        f"Статус: {o['status']}",
        f"Сумма: {o['total_amount']}",
        "",
        "Состав:",
    ]
    for it in items:
        lines.append(f"- {it['name']} x{it['quantity']} = {it['price_at_moment']}")

    await cq.message.edit_text("\n".join(lines), reply_markup=kb_order_card(order_id))


@router.callback_query(F.data == "r:orders")
async def list_orders(cq: CallbackQuery, db: Database):
    ids = await get_admin_restaurant_ids(db, cq.from_user.id)
    if not ids:
        await cq.message.edit_text(
            "Нет доступа.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🏠 Главная", callback_data="r:home"),
                InlineKeyboardButton(text="🔙 Назад", callback_data="r:back:main"),
            ]]),
        )
        await cq.answer()
        return

    restaurant_id = ids[0]  # MVP: первый ресторан админа

    orders = OrdersRepo(db)
    rows = await orders.list_current_for_shop(shop_id=restaurant_id, statuses=CURRENT)
    if not rows:
        await cq.message.edit_text(
            f"Текущих заказов нет (restaurant_id={restaurant_id}).",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🏠 Главная", callback_data="r:home"),
                InlineKeyboardButton(text="🔙 Назад", callback_data="r:back:main"),
            ]]),
        )
        await cq.answer()
        return

    order_ids = [int(r["id"]) for r in rows]
    await cq.message.edit_text(
        f"Текущие заказы (restaurant_id={restaurant_id}):",
        reply_markup=kb_orders_list(order_ids),
    )
    await cq.answer()


@router.callback_query(F.data == "r:chat")
async def list_chats(cq: CallbackQuery, db: Database):
    ids = await get_admin_restaurant_ids(db, cq.from_user.id)
    if not ids:
        await cq.message.edit_text(
            "Нет доступа.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🏠 Главная", callback_data="r:home"),
                InlineKeyboardButton(text="🔙 Назад", callback_data="r:back:main"),
            ]]),
        )
        await cq.answer()
        return
    restaurant_id = ids[0]
    chats = ChatRepo(db)
    rows = await chats.list_active_orders_for_shop(restaurant_id)
    if not rows:
        await cq.message.edit_text("Активных чатов пока нет.", reply_markup=kb_chat_list([]))
        await cq.answer()
        return
    order_ids = [int(r["id"]) for r in rows]
    await cq.message.edit_text("Чаты по заказам:", reply_markup=kb_chat_list(order_ids))
    await cq.answer()


@router.callback_query(F.data.startswith("r:order:"))
async def order_card(cq: CallbackQuery, db: Database):
    order_id = int(cq.data.split(":")[2])
    await render_order_card(cq, db, order_id)
    await cq.answer()


@router.callback_query(F.data.startswith("r:chat:open:"))
async def open_chat(cq: CallbackQuery, state: FSMContext, db: Database):
    order_id = int(cq.data.split(":")[3])
    await state.set_state(ChatStates.chat)
    await state.update_data(order_id=order_id)
    await render_chat_history(cq, db, order_id)
    await cq.answer()


@router.callback_query(F.data.startswith("r:chat:order:"))
async def open_chat_from_order(cq: CallbackQuery, state: FSMContext, db: Database):
    order_id = int(cq.data.split(":")[3])
    await state.set_state(ChatStates.chat)
    await state.update_data(order_id=order_id)
    await render_chat_history(cq, db, order_id)
    await cq.answer()


async def render_chat_history(cq: CallbackQuery, db: Database, order_id: int):
    chats = ChatRepo(db)
    messages = await chats.list_messages(order_id, limit=15)
    lines = [f"💬 Чат по заказу #{order_id}"]
    for msg in reversed(messages):
        role = "Админ" if msg["sender_role"] == "admin" else "Клиент"
        lines.append(f"{role}: {msg['message']}")
    lines.append("\nНапишите сообщение, чтобы отправить его клиенту.")
    await cq.message.edit_text("\n".join(lines), reply_markup=kb_chat_order())


@router.message(ChatStates.chat)
async def send_chat_message(message: Message, state: FSMContext, db: Database):
    text = (message.text or "").strip()
    if not text:
        await message.answer("Сообщение не может быть пустым.")
        return

    data = await state.get_data()
    order_id = data.get("order_id")
    if not order_id:
        await message.answer("Не удалось определить заказ.", reply_markup=kb_admin_main())
        await state.clear()
        return

    chats = ChatRepo(db)
    await chats.add_message(order_id, "admin", message.from_user.id, text)

    orders = OrdersRepo(db)
    order = await orders.get_order(int(order_id))
    if order:
        try:
            await message.bot.send_message(int(order["client_user_id"]), f"Сообщение по заказу #{order_id}: {text}")
        except Exception:
            pass
    await message.answer("Сообщение отправлено. Можете писать дальше.")


@router.callback_query(F.data.startswith("r:st:"))
async def set_status(cq: CallbackQuery, db: Database):
    _, _, order_id_str, status = cq.data.split(":", 3)
    order_id = int(order_id_str)

    orders = OrdersRepo(db)
    await orders.set_status(order_id, status)

    await cq.answer("Статус обновлён")
    await render_order_card(cq, db, order_id)


@router.callback_query(F.data == "r:back:main")
async def back_main(cq: CallbackQuery):
    await cq.message.edit_text("Админ-меню ресторана:", reply_markup=kb_admin_main())
    await cq.answer()
