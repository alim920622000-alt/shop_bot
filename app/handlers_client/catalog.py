from aiogram import Router, F
from app.repositories.admins_repo import AdminsRepo
from aiogram.types import CallbackQuery
from app.db.database import Database
from app.repositories.shops_repo import ShopsRepo
from app.repositories.categories_repo import CategoriesRepo
from app.repositories.products_repo import ProductsRepo
from app.repositories.orders_repo import OrdersRepo
from app.repositories.cart_repo import CartRepo
from app.handlers_client.kb import (
    kb_client_main,
    kb_back,
    kb_shops_list,
    kb_categories_list,
    kb_products_list,
    kb_product_card,
    kb_cart,
    kb_checkout_choose_shop,
    kb_after_order,
)

router = Router()


@router.callback_query(F.data == "c:shops")
async def list_shops(cq: CallbackQuery, db: Database):
    repo = ShopsRepo(db)
    items = await repo.list_active(business_type="shop")

    if not items:
        await cq.message.edit_text("Магазинов пока нет.", reply_markup=kb_back("main"))
        await cq.answer()
        return

    await cq.message.edit_text("Выберите магазин:", reply_markup=kb_shops_list(items, "shop"))
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
        await cq.message.edit_text("Ресторанов пока нет.", reply_markup=kb_back("main"))
        await cq.answer()
        return

    await cq.message.edit_text("Выберите ресторан:", reply_markup=kb_shops_list(items, "restaurant"))
    await cq.answer()


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
        await cq.message.edit_text("В этой категории пока нет товаров.", reply_markup=kb_back("main"))
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
        await cq.message.edit_text("Товар не найден.", reply_markup=kb_back("main"))
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
        await cq.message.edit_text("Точка не найдена.", reply_markup=kb_back("main"))
        await cq.answer()
        return

    cats = CategoriesRepo(db)
    categories = await cats.list_for_shop(shop_id, active_only=True)
    if not categories:
        await cq.message.edit_text("Категорий пока нет.", reply_markup=kb_back("main"))
        await cq.answer()
        return

    title = "Категории магазина:" if shop["business_type"] == "shop" else "Категории ресторана:"
    await cq.message.edit_text(title, reply_markup=kb_categories_list(categories, shop["business_type"], shop_id))
    await cq.answer()


@router.callback_query(F.data.startswith("c:back:"))
async def back(cq: CallbackQuery):
    target = cq.data.split(":", 2)[2]

    if target == "main":
        await cq.message.edit_text("Выберите раздел:", reply_markup=kb_client_main())
        await cq.answer()
        return

    if target == "shop_list":
        # вернуться в список магазинов
        await cq.message.edit_text("Выберите раздел:", reply_markup=kb_client_main())
        # затем пользователь нажмёт "Магазины" снова (MVP)
        await cq.answer()
        return

    if target == "restaurant_list":
        await cq.message.edit_text("Выберите раздел:", reply_markup=kb_client_main())
        await cq.answer()
        return

    if target == "cart":
        cq.data = "c:cart"
        await open_cart(cq, db)  # <-- тут нужен db, поэтому проще сделать отдельный back ниже

    await cq.answer("Неизвестный переход", show_alert=True)


async def render_cart(message, user_id: int, db: Database):
    cart = CartRepo(db)
    items = await cart.list_items(user_id)

    if not items:
        await message.edit_text("Корзина пуста.", reply_markup=kb_back("main"))
        return

    total = sum(float(i["price"]) * int(i["quantity"]) for i in items)
    text_lines = ["🧺 Корзина:"]
    for i in items:
        line_total = float(i["price"]) * int(i["quantity"])
        text_lines.append(f"- {i['name']} x{i['quantity']} = {line_total}")
    text_lines.append(f"\nИтого: {total}")

    await message.edit_text("\n".join(text_lines), reply_markup=kb_cart(items))


@router.callback_query(F.data == "c:cart")
async def open_cart(cq: CallbackQuery, db: Database):
    await render_cart(cq.message, cq.from_user.id, db)
    await cq.answer()


@router.callback_query(F.data == "c:noop")
async def noop(cq: CallbackQuery):
    await cq.answer()


@router.callback_query(F.data.startswith("c:cart_inc:"))
async def cart_inc(cq: CallbackQuery, db: Database):
    product_id = int(cq.data.split(":")[2])
    cart = CartRepo(db)
    await cart.add(user_id=cq.from_user.id, product_id=product_id, qty=1)
    await cq.answer("Ок")
    # обновим экран корзины
    await cq.answer("Ок")
    await render_cart(cq.message, cq.from_user.id, db)


@router.callback_query(F.data.startswith("c:cart_dec:"))
async def cart_dec(cq: CallbackQuery, db: Database):
    product_id = int(cq.data.split(":")[2])
    cart = CartRepo(db)
    items = await cart.list_items(cq.from_user.id)
    current = next((x for x in items if x["product_id"] == product_id), None)
    if not current:
        await cq.answer("Нет в корзине", show_alert=True)
        return
    new_qty = int(current["quantity"]) - 1
    await cart.set_qty(user_id=cq.from_user.id, product_id=product_id, qty=new_qty)
    await cq.answer("Ок")
    await render_cart(cq.message, cq.from_user.id, db)


@router.callback_query(F.data.startswith("c:cart_del:"))
async def cart_del(cq: CallbackQuery, db: Database):
    product_id = int(cq.data.split(":")[2])
    cart = CartRepo(db)
    await cart.set_qty(user_id=cq.from_user.id, product_id=product_id, qty=0)
    await cq.answer("Удалено")
    await render_cart(cq.message, cq.from_user.id, db)


@router.callback_query(F.data == "c:checkout")
async def checkout(cq: CallbackQuery, db: Database):
    cart = CartRepo(db)
    items = await cart.list_items(cq.from_user.id)
    if not items:
        await cq.message.edit_text("Корзина пуста.", reply_markup=kb_back("main"))
        await cq.answer()
        return

    shop_ids = sorted({int(i["shop_id"]) for i in items})
    if len(shop_ids) == 1:
        # оформляем сразу
        await _create_order_for_shop(cq, db, shop_ids[0])
        return

    # если в корзине товары из разных точек — выбрать
    await cq.message.edit_text(
        "В корзине товары из разных магазинов/ресторанов. Выберите, для какой точки оформить заказ:",
        reply_markup=kb_checkout_choose_shop(shop_ids),
    )
    await cq.answer()


@router.callback_query(F.data.startswith("c:checkout_shop:"))
async def _create_order_for_shop(cq: CallbackQuery, db: Database, shop_id: int):
    orders = OrdersRepo(db)

    # 1) создаём заказ
    try:
        order_id = await orders.create_order_from_cart(shop_id=shop_id, client_user_id=cq.from_user.id)
    except ValueError:
        await cq.message.edit_text(
            "Не удалось создать заказ: корзина пуста для этой точки.",
            reply_markup=kb_back("main"),
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


@router.callback_query(F.data == "c:back:cart")
async def back_to_cart(cq: CallbackQuery, db: Database):
    await open_cart(cq, db)
    await cq.answer()
