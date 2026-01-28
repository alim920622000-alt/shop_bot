from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.db.database import Database
from app.handlers_admin_restaurant.utils import is_restaurant_admin, get_admin_restaurant_ids
from app.handlers_admin_restaurant.start import kb_admin_main
from app.repositories.orders_repo import OrdersRepo
from app.repositories.promotions_repo import PromotionsRepo
from app.repositories.products_repo import ProductsRepo
from app.repositories.categories_repo import CategoriesRepo
from app.repositories.shops_repo import ShopsRepo

router = Router()


class PromoStates(StatesGroup):
    add_name = State()
    add_desc = State()


def kb_back_home() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главная", callback_data="r:home")]
    ])


def kb_back_promos() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="r:promos")],
        [InlineKeyboardButton(text="🏠 Главная", callback_data="r:home")],
    ])


def kb_history_list(order_ids: list[int]) -> InlineKeyboardMarkup:
    kb = []
    for oid in order_ids:
        kb.append([InlineKeyboardButton(text=f"Заказ #{oid}", callback_data=f"r:history_order:{oid}")])
    kb.append([InlineKeyboardButton(text="🏠 Главная", callback_data="r:home")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def kb_history_card() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="r:history")],
        [InlineKeyboardButton(text="🏠 Главная", callback_data="r:home")],
    ])


def kb_promos_list(promos: list[dict]) -> InlineKeyboardMarkup:
    kb = []
    for promo in promos:
        kb.append([InlineKeyboardButton(text=promo["name"], callback_data=f"r:promo:{promo['id']}")])
    kb.append([InlineKeyboardButton(text="➕ Добавить акцию", callback_data="r:promo_add")])
    kb.append([InlineKeyboardButton(text="🏠 Главная", callback_data="r:home")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def kb_promo_card(promo_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📌 Выбрать позиции", callback_data=f"r:promo_pick:{promo_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="r:promos")],
    ])


def kb_promo_categories(promo_id: int, categories: list[dict]) -> InlineKeyboardMarkup:
    kb = []
    for cat in categories:
        kb.append([InlineKeyboardButton(
            text=cat["name"],
            callback_data=f"r:promo_cat:{promo_id}:{cat['id']}",
        )])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"r:promo:{promo_id}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def kb_promo_products(promo_id: int, category_id: int, products: list[dict], chosen_ids: set[int]) -> InlineKeyboardMarkup:
    kb = []
    for p in products:
        mark = "✅" if int(p["id"]) in chosen_ids else "➕"
        kb.append([InlineKeyboardButton(
            text=f"{mark} {p['name']} — {p['price']}",
            callback_data=f"r:promo_toggle:{promo_id}:{category_id}:{p['id']}",
        )])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"r:promo_pick:{promo_id}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


async def _guard_admin(db: Database, user_id: int) -> bool:
    return await is_restaurant_admin(db, user_id)


async def _get_restaurant_id(db: Database, user_id: int) -> int | None:
    ids = await get_admin_restaurant_ids(db, user_id)
    return ids[0] if ids else None


@router.callback_query(F.data == "r:history")
async def history(cq: CallbackQuery, db: Database):
    if not await _guard_admin(db, cq.from_user.id):
        await cq.answer("Нет доступа", show_alert=True)
        return
    restaurant_id = await _get_restaurant_id(db, cq.from_user.id)
    if not restaurant_id:
        await cq.message.edit_text("Нет привязанного ресторана.", reply_markup=kb_back_home())
        await cq.answer()
        return
    orders = OrdersRepo(db)
    rows = await orders.list_history_for_shop(restaurant_id, statuses=["finished", "canceled"])
    if not rows:
        await cq.message.edit_text("История заказов пуста.", reply_markup=kb_back_home())
        await cq.answer()
        return
    order_ids = [int(r["id"]) for r in rows]
    await cq.message.edit_text("История заказов:", reply_markup=kb_history_list(order_ids))
    await cq.answer()


@router.callback_query(F.data.startswith("r:history_order:"))
async def history_order_card(cq: CallbackQuery, db: Database):
    order_id = int(cq.data.split(":")[2])
    orders = OrdersRepo(db)
    o = await orders.get_order(order_id)
    if not o:
        await cq.message.edit_text("Заказ не найден.", reply_markup=kb_back_home())
        await cq.answer()
        return
    items = await orders.get_order_items(order_id)
    lines = [f"Заказ #{o['id']}", f"Статус: {o['status']}", f"Сумма: {o['total_amount']}", "", "Состав:"]
    for it in items:
        lines.append(f"- {it['name']} x{it['quantity']} = {it['price_at_moment']}")
    await cq.message.edit_text("\n".join(lines), reply_markup=kb_history_card())
    await cq.answer()


@router.callback_query(F.data == "r:promos")
async def promos(cq: CallbackQuery, db: Database):
    if not await _guard_admin(db, cq.from_user.id):
        await cq.answer("Нет доступа", show_alert=True)
        return
    restaurant_id = await _get_restaurant_id(db, cq.from_user.id)
    if not restaurant_id:
        await cq.message.edit_text("Нет привязанного ресторана.", reply_markup=kb_back_home())
        await cq.answer()
        return
    repo = PromotionsRepo(db)
    promos_list = await repo.list_for_shop(restaurant_id)
    if not promos_list:
        await cq.message.edit_text("Акций пока нет.", reply_markup=kb_promos_list([]))
        await cq.answer()
        return
    await cq.message.edit_text("Список акций:", reply_markup=kb_promos_list(list(promos_list)))
    await cq.answer()


@router.callback_query(F.data == "r:promo_add")
async def promo_add_start(cq: CallbackQuery, state: FSMContext):
    await state.set_state(PromoStates.add_name)
    await cq.message.edit_text("Введите название акции:", reply_markup=kb_back_home())
    await cq.answer()


@router.message(PromoStates.add_name)
async def promo_add_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Название слишком короткое. Введите ещё раз:")
        return
    await state.update_data(name=name)
    await state.set_state(PromoStates.add_desc)
    await message.answer("Введите описание или отправьте '-' чтобы пропустить:")


@router.message(PromoStates.add_desc)
async def promo_add_desc(message: Message, state: FSMContext, db: Database):
    if not await is_restaurant_admin(db, message.from_user.id):
        await message.answer("Нет доступа.")
        return
    desc = (message.text or "").strip()
    if desc == "-":
        desc = ""
    data = await state.get_data()
    name = data.get("name", "")
    restaurant_id = await _get_restaurant_id(db, message.from_user.id)
    if not restaurant_id:
        await message.answer("Нет привязанного ресторана.", reply_markup=kb_admin_main())
        await state.clear()
        return
    repo = PromotionsRepo(db)
    await repo.create(restaurant_id, name, desc)
    await state.clear()
    await message.answer("Акция создана ✅", reply_markup=kb_admin_main())


@router.callback_query(F.data.startswith("r:promo:"))
async def promo_card(cq: CallbackQuery, db: Database):
    promo_id = int(cq.data.split(":")[2])
    repo = PromotionsRepo(db)
    promo = await repo.get(promo_id)
    if not promo:
        await cq.message.edit_text("Акция не найдена.", reply_markup=kb_back_home())
        await cq.answer()
        return
    items = await repo.list_items(promo_id)
    text = (
        f"🎁 {promo['name']}\n"
        f"Описание: {promo.get('description') or '—'}\n"
        f"Позиции в акции: {len(items)}"
    )
    await cq.message.edit_text(text, reply_markup=kb_promo_card(promo_id))
    await cq.answer()


@router.callback_query(F.data.startswith("r:promo_pick:"))
async def promo_pick_category(cq: CallbackQuery, db: Database):
    promo_id = int(cq.data.split(":")[2])
    restaurant_id = await _get_restaurant_id(db, cq.from_user.id)
    if not restaurant_id:
        await cq.message.edit_text("Нет привязанного ресторана.", reply_markup=kb_back_home())
        await cq.answer()
        return
    cats = CategoriesRepo(db)
    categories = await cats.list_for_shop(restaurant_id, active_only=True)
    if not categories:
        await cq.message.edit_text("Категорий пока нет.", reply_markup=kb_back_promos())
        await cq.answer()
        return
    await cq.message.edit_text("Выберите категорию:", reply_markup=kb_promo_categories(promo_id, list(categories)))
    await cq.answer()


@router.callback_query(F.data.startswith("r:promo_cat:"))
async def promo_pick_product(cq: CallbackQuery, db: Database):
    _, _, promo_id_str, category_id_str = cq.data.split(":", 3)
    promo_id = int(promo_id_str)
    category_id = int(category_id_str)
    products_repo = ProductsRepo(db)
    products = await products_repo.list_by_category(category_id, active_only=False)
    promo_repo = PromotionsRepo(db)
    chosen = await promo_repo.list_items(promo_id)
    chosen_ids = {int(p["id"]) for p in chosen}
    await cq.message.edit_text(
        "Выберите позиции для акции:",
        reply_markup=kb_promo_products(promo_id, category_id, list(products), chosen_ids),
    )
    await cq.answer()


@router.callback_query(F.data.startswith("r:promo_toggle:"))
async def promo_toggle_product(cq: CallbackQuery, db: Database):
    _, _, promo_id_str, category_id_str, product_id_str = cq.data.split(":", 4)
    promo_id = int(promo_id_str)
    category_id = int(category_id_str)
    product_id = int(product_id_str)
    repo = PromotionsRepo(db)
    await repo.toggle_product(promo_id, product_id)
    await promo_pick_product(cq, db)


@router.callback_query(F.data == "r:cabinet")
async def cabinet(cq: CallbackQuery, db: Database):
    if not await _guard_admin(db, cq.from_user.id):
        await cq.answer("Нет доступа", show_alert=True)
        return
    restaurant_id = await _get_restaurant_id(db, cq.from_user.id)
    if not restaurant_id:
        await cq.message.edit_text("Нет привязанного ресторана.", reply_markup=kb_back_home())
        await cq.answer()
        return
    repo = ShopsRepo(db)
    shop = await repo.get(restaurant_id)
    if not shop:
        await cq.message.edit_text("Ресторан не найден.", reply_markup=kb_back_home())
        await cq.answer()
        return
    text = (
        "👤 Кабинет ресторана (только просмотр)\n"
        f"Телефон: {shop.get('phone') or '—'}\n"
        f"Адрес: {shop.get('address') or '—'}\n"
        f"Лого: {shop.get('logo_url') or '—'}\n"
        f"О компании: {shop.get('about') or '—'}"
    )
    await cq.message.edit_text(text, reply_markup=kb_back_home())
    await cq.answer()
