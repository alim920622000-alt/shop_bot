from aiogram import Router, F
from app.repositories.admins_repo import AdminsRepo
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.db.database import Database
from app.repositories.shops_repo import ShopsRepo
from app.repositories.categories_repo import CategoriesRepo
from app.repositories.products_repo import ProductsRepo
from app.repositories.orders_repo import OrdersRepo
from app.repositories.cart_repo import CartRepo
from app.repositories.chat_repo import ChatRepo
from app.repositories.client_profile_repo import ClientProfileRepo
from app.services.search_service import SearchService
from app.handlers_client.kb import (
    kb_client_main,
    kb_client_order_menu,
    kb_back,
    kb_shops_list,
    kb_categories_list,
    kb_products_list,
    kb_product_card,
    kb_cart,
    kb_checkout_choose_shop,
    kb_after_order,
    kb_cart_choose,
    kb_search_choose,
    kb_orders_list,
    kb_order_card,
    kb_chat_list,
    kb_cabinet,
    kb_chat_order,
)

router = Router()


class ClientStates(StatesGroup):
    search = State()
    chat = State()
    cabinet_full_name = State()
    cabinet_phone = State()
    cabinet_address = State()


@router.callback_query(F.data == "c:shops")
async def list_shops(cq: CallbackQuery, db: Database):
    repo = ShopsRepo(db)
    items = await repo.list_active(business_type="shop")

    if not items:
        await cq.message.edit_text("Магазинов пока нет.", reply_markup=kb_back("order"))
        await cq.answer()
        return

    await cq.message.edit_text("Выберите магазин:", reply_markup=kb_shops_list(items, "shop"))
    await cq.answer()


@router.callback_query(F.data == "c:order")
async def order_menu(cq: CallbackQuery):
    await cq.message.edit_text("Выберите раздел заказа:", reply_markup=kb_client_order_menu())
    await cq.answer()


@router.callback_query(F.data == "c:home")
async def client_home(cq: CallbackQuery):
    await cq.message.edit_text("Выберите раздел:", reply_markup=kb_client_main())
    await cq.answer()


@router.callback_query(F.data == "c:restaurants")
async def list_restaurants(cq: CallbackQuery, db: Database):
    repo = ShopsRepo(db)
    items = await repo.list_active(business_type="restaurant")

    if not items:
        await cq.message.edit_text("Ресторанов пока нет.", reply_markup=kb_back("order"))
        await cq.answer()
        return

    await cq.message.edit_text("Выберите ресторан:", reply_markup=kb_shops_list(items, "restaurant"))
    await cq.answer()


@router.callback_query(F.data == "c:cart:choose")
async def cart_choose(cq: CallbackQuery):
    await cq.message.edit_text("Выберите корзину:", reply_markup=kb_cart_choose())
    await cq.answer()


@router.callback_query(F.data == "c:search:choose")
async def search_choose(cq: CallbackQuery):
    await cq.message.edit_text("Выберите, где искать:", reply_markup=kb_search_choose())
    await cq.answer()


@router.callback_query(F.data.startswith("c:search:"))
async def search_start(cq: CallbackQuery, state: FSMContext):
    _, _, business_type = cq.data.split(":", 2)
    if business_type not in {"shop", "restaurant"}:
        await cq.answer("Неизвестный тип поиска", show_alert=True)
        return
    await state.set_state(ClientStates.search)
    await state.update_data(business_type=business_type)
    await cq.message.edit_text(
        "Введите запрос для поиска товаров. Можно вводить по мере уточнения:",
        reply_markup=kb_back("order"),
    )
    await cq.answer()


@router.message(ClientStates.search)
async def search_products(message: Message, state: FSMContext, db: Database):
    data = await state.get_data()
    business_type = data.get("business_type")
    if business_type not in {"shop", "restaurant"}:
        await message.answer("Неизвестный тип поиска.", reply_markup=kb_client_order_menu())
        await state.clear()
        return

    query = (message.text or "").strip()
    service = SearchService(db)
    results = await service.search_products(query, business_type=business_type, limit=10, active_only=True)
    if not results:
        await message.answer("Ничего не найдено. Попробуйте уточнить запрос.")
        return

    lines = ["Результаты поиска:"]
    for item in results:
        lines.append(f"- {item['name']} — {item['price']} (id: {item['id']})")
    lines.append("\nЧтобы открыть товар, используйте его ID из списка в разделе магазина.")
    await message.answer("\n".join(lines))


@router.callback_query(F.data.startswith("c:pick:"))
async def pick_shop(cq: CallbackQuery, db: Database):
    # c:pick:{kind}:{shop_id}
    _, _, kind, shop_id_str = cq.data.split(":", 3)
    shop_id = int(shop_id_str)

    cats = CategoriesRepo(db)
    categories = await cats.list_for_shop(shop_id, active_only=True)
    if not categories:
        await cq.message.edit_text("Категорий пока нет.", reply_markup=kb_back(f"{kind}_list"))
        await cq.answer()
        return

    title = "Категории магазина:" if kind == "shop" else "Категории ресторана:"
    await cq.message.edit_text(title, reply_markup=kb_categories_list(categories, kind, shop_id))
    await cq.answer()


@router.callback_query(F.data.startswith("c:cat:"))
async def open_category(cq: CallbackQuery, db: Database):
    # c:cat:{shop_id}:{category_id}
    _, _, shop_id_str, category_id_str = cq.data.split(":", 3)
    shop_id = int(shop_id_str)
    category_id = int(category_id_str)

    prod = ProductsRepo(db)
    products = await prod.list_by_category(category_id, active_only=True)

    if not products:
        await cq.message.edit_text("В этой категории пока нет товаров.", reply_markup=kb_back("order"))
        await cq.answer()
        return

    await cq.message.edit_text(
        "Список товаров:",
        reply_markup=kb_products_list(products, shop_id, category_id)
    )
    await cq.answer()


@router.callback_query(F.data.startswith("c:prod:"))
async def open_product(cq: CallbackQuery, db: Database):
    # c:prod:{product_id}
    product_id = int(cq.data.split(":")[2])

    prod = ProductsRepo(db)
    p = await prod.get(product_id)
    if not p:
        await cq.message.edit_text("Товар не найден.", reply_markup=kb_back("order"))
        await cq.answer()
        return

    text = f"{p['name']}\n\nЦена: {p['price']}\n"
    if p.get("description"):
        text += f"\nОписание: {p['description']}\n"

    await cq.message.edit_text(
        text,
        reply_markup=kb_product_card(product_id=product_id, shop_id=p["shop_id"], category_id=p["category_id"])
    )
    await cq.answer()


@router.callback_query(F.data.startswith("c:add:"))
async def add_to_cart(cq: CallbackQuery, db: Database):
    # c:add:{product_id}
    product_id = int(cq.data.split(":")[2])

    prod = ProductsRepo(db)
    p = await prod.get(product_id)
    if not p:
        await cq.answer("Товар не найден", show_alert=True)
        return

    cart = CartRepo(db)
    await cart.add(user_id=cq.from_user.id, product_id=product_id, qty=1)

    await cq.answer("Добавлено в корзину")


@router.callback_query(F.data.startswith("c:pickback:"))
async def back_to_categories(cq: CallbackQuery, db: Database):
    # c:pickback:{shop_id}
    shop_id = int(cq.data.split(":")[2])

    # Определяем тип точки, чтобы правильный заголовок показать
    shops = ShopsRepo(db)
    shop = await shops.get(shop_id)
    if not shop:
        await cq.message.edit_text("Точка не найдена.", reply_markup=kb_back("order"))
        await cq.answer()
        return

    cats = CategoriesRepo(db)
    categories = await cats.list_for_shop(shop_id, active_only=True)
    if not categories:
        await cq.message.edit_text("Категорий пока нет.", reply_markup=kb_back("order"))
        await cq.answer()
        return

    title = "Категории магазина:" if shop["business_type"] == "shop" else "Категории ресторана:"
    await cq.message.edit_text(title, reply_markup=kb_categories_list(categories, shop["business_type"], shop_id))
    await cq.answer()


@router.callback_query(F.data.startswith("c:back:"))
async def back(cq: CallbackQuery, state: FSMContext):
    target = cq.data.split(":", 2)[2]

    if target in {"main", "home"}:
        await state.clear()
        await cq.message.edit_text("Выберите раздел:", reply_markup=kb_client_main())
        await cq.answer()
        return

    if target == "order":
        await state.clear()
        await cq.message.edit_text("Выберите раздел заказа:", reply_markup=kb_client_order_menu())
        await cq.answer()
        return

    await cq.answer("Неизвестный переход", show_alert=True)


async def render_cart(message, user_id: int, db: Database, business_type: str):
    cart = CartRepo(db)
    items = await cart.list_items(user_id, business_type=business_type)

    if not items:
        await message.edit_text("Корзина пуста.", reply_markup=kb_back("order"))
        return

    total = sum(float(i["price"]) * int(i["quantity"]) for i in items)
    text_lines = ["🧺 Корзина:"]
    for i in items:
        line_total = float(i["price"]) * int(i["quantity"])
        text_lines.append(f"- {i['name']} x{i['quantity']} = {line_total}")
    text_lines.append(f"\nИтого: {total}")

    await message.edit_text("\n".join(text_lines), reply_markup=kb_cart(items, business_type))


@router.callback_query(F.data.startswith("c:cart:"))
async def open_cart(cq: CallbackQuery, db: Database):
    _, _, business_type = cq.data.split(":", 2)
    if business_type not in {"shop", "restaurant"}:
        await cq.answer("Неизвестный тип корзины", show_alert=True)
        return
    await render_cart(cq.message, cq.from_user.id, db, business_type)
    await cq.answer()


@router.callback_query(F.data == "c:noop")
async def noop(cq: CallbackQuery):
    await cq.answer()


@router.callback_query(F.data.startswith("c:cart_inc:"))
async def cart_inc(cq: CallbackQuery, db: Database):
    _, _, business_type, product_id_str = cq.data.split(":", 3)
    product_id = int(product_id_str)
    cart = CartRepo(db)
    await cart.add(user_id=cq.from_user.id, product_id=product_id, qty=1)
    await cq.answer("Ок")
    # обновим экран корзины
    await cq.answer("Ок")
    await render_cart(cq.message, cq.from_user.id, db, business_type)


@router.callback_query(F.data.startswith("c:cart_dec:"))
async def cart_dec(cq: CallbackQuery, db: Database):
    _, _, business_type, product_id_str = cq.data.split(":", 3)
    product_id = int(product_id_str)
    cart = CartRepo(db)
    items = await cart.list_items(cq.from_user.id, business_type=business_type)
    current = next((x for x in items if x["product_id"] == product_id), None)
    if not current:
        await cq.answer("Нет в корзине", show_alert=True)
        return
    new_qty = int(current["quantity"]) - 1
    await cart.set_qty(user_id=cq.from_user.id, product_id=product_id, qty=new_qty)
    await cq.answer("Ок")
    await render_cart(cq.message, cq.from_user.id, db, business_type)


@router.callback_query(F.data.startswith("c:cart_del:"))
async def cart_del(cq: CallbackQuery, db: Database):
    _, _, business_type, product_id_str = cq.data.split(":", 3)
    product_id = int(product_id_str)
    cart = CartRepo(db)
    await cart.set_qty(user_id=cq.from_user.id, product_id=product_id, qty=0)
    await cq.answer("Удалено")
    await render_cart(cq.message, cq.from_user.id, db, business_type)


@router.callback_query(F.data.startswith("c:checkout:"))
async def checkout(cq: CallbackQuery, db: Database):
    _, _, business_type = cq.data.split(":", 2)
    cart = CartRepo(db)
    items = await cart.list_items(cq.from_user.id, business_type=business_type)
    if not items:
        await cq.message.edit_text("Корзина пуста.", reply_markup=kb_back("order"))
        await cq.answer()
        return

    shop_ids = sorted({int(i["shop_id"]) for i in items})
    if len(shop_ids) == 1:
        # оформляем сразу
        await _create_order_for_shop(cq, db, shop_ids[0], business_type)
        return

    # если в корзине товары из разных точек — выбрать
    await cq.message.edit_text(
        "В корзине товары из разных магазинов/ресторанов. Выберите, для какой точки оформить заказ:",
        reply_markup=kb_checkout_choose_shop(shop_ids, business_type),
    )
    await cq.answer()


@router.callback_query(F.data.startswith("c:checkout_shop:"))
async def _create_order_for_shop(cq: CallbackQuery, db: Database, shop_id: int | None = None, business_type: str | None = None):
    if shop_id is None:
        _, _, business_type, shop_id_str = cq.data.split(":", 3)
        shop_id = int(shop_id_str)
    orders = OrdersRepo(db)

    # 1) создаём заказ
    try:
        order_id = await orders.create_order_from_cart(shop_id=shop_id, client_user_id=cq.from_user.id)
    except ValueError:
        await cq.message.edit_text(
            "Не удалось создать заказ: корзина пуста для этой точки.",
            reply_markup=kb_back("order"),
        )
        await cq.answer()
        return

    # 2) уведомляем админов точки (MVP: уведомление из клиентского бота)
    admins = AdminsRepo(db)
    admin_ids = await admins.list_admin_user_ids(shop_id)

    note = (
        f"🔔 Новый заказ #{order_id}\n"
        f"Точка (shop_id): {shop_id}\n"
        f"Статус: new"
    )

    for uid in admin_ids:
        try:
            await cq.bot.send_message(uid, note)
        except Exception:
            pass

    # 3) ответ клиенту
    await cq.message.edit_text(
        f"✅ Заказ успешно создан!\nНомер заказа: {order_id}\nСтатус: new",
        reply_markup=kb_after_order(),
    )
    await cq.answer()


@router.callback_query(F.data == "c:orders")
async def list_orders(cq: CallbackQuery, db: Database):
    orders = OrdersRepo(db)
    rows = await orders.list_for_client(cq.from_user.id)
    if not rows:
        await cq.message.edit_text("Заказов пока нет.", reply_markup=kb_back("main"))
        await cq.answer()
        return
    order_ids = [int(r["id"]) for r in rows]
    await cq.message.edit_text("Ваши заказы:", reply_markup=kb_orders_list(order_ids, "c:order_view"))
    await cq.answer()


@router.callback_query(F.data == "c:history")
async def list_history(cq: CallbackQuery, db: Database):
    history_statuses = ["ready", "finished", "delivered", "canceled"]
    orders = OrdersRepo(db)
    rows = await orders.list_for_client(cq.from_user.id, statuses=history_statuses)
    if not rows:
        await cq.message.edit_text("История пуста.", reply_markup=kb_back("order"))
        await cq.answer()
        return
    order_ids = [int(r["id"]) for r in rows]
    await cq.message.edit_text("История заказов:", reply_markup=kb_orders_list(order_ids, "c:order_view"))
    await cq.answer()


@router.callback_query(F.data.startswith("c:order_view:"))
async def order_card(cq: CallbackQuery, db: Database):
    order_id = int(cq.data.split(":")[2])
    orders = OrdersRepo(db)
    o = await orders.get_order(order_id)
    if not o:
        await cq.message.edit_text("Заказ не найден.", reply_markup=kb_back("main"))
        await cq.answer()
        return
    items = await orders.get_order_items(order_id)
    lines = [f"Заказ #{o['id']}", f"Статус: {o['status']}", f"Сумма: {o['total_amount']}", "", "Состав:"]
    for it in items:
        lines.append(f"- {it['name']} x{it['quantity']} = {it['price_at_moment']}")
    await cq.message.edit_text("\n".join(lines), reply_markup=kb_order_card(order_id))
    await cq.answer()


@router.callback_query(F.data == "c:chat")
async def list_chats(cq: CallbackQuery, db: Database):
    chats = ChatRepo(db)
    rows = await chats.list_active_orders_for_client(cq.from_user.id)
    if not rows:
        await cq.message.edit_text("Активных чатов пока нет.", reply_markup=kb_back("main"))
        await cq.answer()
        return
    order_ids = [int(r["id"]) for r in rows]
    await cq.message.edit_text("Чаты по заказам:", reply_markup=kb_chat_list(order_ids, "c:chat:open"))
    await cq.answer()


@router.callback_query(F.data.startswith("c:chat:open:"))
async def open_chat(cq: CallbackQuery, state: FSMContext, db: Database):
    order_id = int(cq.data.split(":")[3])
    await state.set_state(ClientStates.chat)
    await state.update_data(order_id=order_id)
    await render_chat_history(cq, db, order_id)
    await cq.answer()


@router.callback_query(F.data.startswith("c:chat:order:"))
async def open_chat_from_order(cq: CallbackQuery, state: FSMContext, db: Database):
    order_id = int(cq.data.split(":")[3])
    await state.set_state(ClientStates.chat)
    await state.update_data(order_id=order_id)
    await render_chat_history(cq, db, order_id)
    await cq.answer()


async def render_chat_history(cq: CallbackQuery, db: Database, order_id: int):
    chats = ChatRepo(db)
    messages = await chats.list_messages(order_id, limit=15)
    lines = [f"💬 Чат по заказу #{order_id}"]
    for msg in reversed(messages):
        role = "Клиент" if msg["sender_role"] == "client" else "Админ"
        lines.append(f"{role}: {msg['message']}")
    lines.append("\nОтправьте сообщение, чтобы написать в чат.")
    await cq.message.edit_text("\n".join(lines), reply_markup=kb_chat_order())


@router.message(ClientStates.chat)
async def send_chat_message(message: Message, state: FSMContext, db: Database):
    text = (message.text or "").strip()
    if not text:
        await message.answer("Сообщение не может быть пустым.")
        return

    data = await state.get_data()
    order_id = data.get("order_id")
    if not order_id:
        await message.answer("Не удалось определить заказ.", reply_markup=kb_client_main())
        await state.clear()
        return

    chats = ChatRepo(db)
    await chats.add_message(order_id, "client", message.from_user.id, text)

    orders = OrdersRepo(db)
    order = await orders.get_order(order_id)
    if order:
        admins = AdminsRepo(db)
        admin_ids = await admins.list_admin_user_ids(int(order["shop_id"]))
        for uid in admin_ids:
            try:
                await message.bot.send_message(uid, f"Сообщение по заказу #{order_id}: {text}")
            except Exception:
                pass

    await message.answer("Сообщение отправлено. Можете писать дальше.")


@router.callback_query(F.data == "c:cabinet")
async def cabinet(cq: CallbackQuery, db: Database):
    repo = ClientProfileRepo(db)
    profile = await repo.get(cq.from_user.id) or {"full_name": "", "phone": "", "address": ""}
    text = (
        "👤 Кабинет\n"
        f"ФИО: {profile.get('full_name') or '—'}\n"
        f"Телефон: {profile.get('phone') or '—'}\n"
        f"Адрес: {profile.get('address') or '—'}"
    )
    await cq.message.edit_text(text, reply_markup=kb_cabinet())
    await cq.answer()


@router.callback_query(F.data.startswith("c:cabinet:edit:"))
async def cabinet_edit(cq: CallbackQuery, state: FSMContext):
    field = cq.data.split(":")[3]
    if field == "full_name":
        await state.set_state(ClientStates.cabinet_full_name)
        await cq.message.edit_text("Введите ФИО:", reply_markup=kb_back("main"))
    elif field == "phone":
        await state.set_state(ClientStates.cabinet_phone)
        await cq.message.edit_text("Введите телефон:", reply_markup=kb_back("main"))
    elif field == "address":
        await state.set_state(ClientStates.cabinet_address)
        await cq.message.edit_text("Введите адрес:", reply_markup=kb_back("main"))
    else:
        await cq.answer("Неизвестное поле", show_alert=True)
        return
    await cq.answer()


@router.message(ClientStates.cabinet_full_name)
async def cabinet_full_name(message: Message, state: FSMContext, db: Database):
    await _update_profile_field(message, state, db, "full_name")


@router.message(ClientStates.cabinet_phone)
async def cabinet_phone(message: Message, state: FSMContext, db: Database):
    await _update_profile_field(message, state, db, "phone")


@router.message(ClientStates.cabinet_address)
async def cabinet_address(message: Message, state: FSMContext, db: Database):
    await _update_profile_field(message, state, db, "address")


async def _update_profile_field(message: Message, state: FSMContext, db: Database, field: str):
    value = (message.text or "").strip()
    if not value:
        await message.answer("Поле не может быть пустым.")
        return
    repo = ClientProfileRepo(db)
    current = await repo.get(message.from_user.id) or {"full_name": "", "phone": "", "address": ""}
    current[field] = value
    await repo.upsert(
        message.from_user.id,
        current.get("full_name", ""),
        current.get("phone", ""),
        current.get("address", ""),
    )
    await state.clear()
    await message.answer("Данные обновлены.", reply_markup=kb_client_main())
