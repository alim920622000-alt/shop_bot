from aiogram import Router, F
from io import BytesIO
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from app.db.database import Database
from app.handlers_admin_shop.utils import get_admin_shop_ids, is_shop_admin
from app.handlers_admin_shop.start import kb_admin_main
from app.repositories.products_repo import ProductsRepo
from app.services.search_service import SearchService
from app.utils import normalize

router = Router()


class ProductStates(StatesGroup):
    add_category = State()
    add_product = State()
    search = State()
    bulk_upload = State()
    bulk_confirm = State()


def kb_home() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главная", callback_data="a:home")]
    ])


def kb_categories(cats: list[dict]) -> InlineKeyboardMarkup:
    kb = []
    for c in cats:
        status = "✅" if int(c["is_active"]) == 1 else "⛔"
        kb.append([InlineKeyboardButton(
            text=f"{status} {c['name']}",
            callback_data=f"a:pcat:{c['id']}"
        )])

    kb.append([InlineKeyboardButton(text="➕ Добавить категорию", callback_data="a:paddcat")])
    kb.append([InlineKeyboardButton(text="🔎 Поиск товара", callback_data="a:psearch")])
    kb.append([InlineKeyboardButton(text="🏠 Главная", callback_data="a:home")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def kb_products(cat_id: int, items: list[dict]) -> InlineKeyboardMarkup:
    kb = []
    for p in items:
        status = "✅" if int(p["is_active"]) == 1 else "⛔"
        kb.append([InlineKeyboardButton(
            text=f"{status} {p['name']} — {p['price']}",
            callback_data=f"a:pprod:{cat_id}:{p['id']}"
        )])

    kb.append([InlineKeyboardButton(text="➕ Добавить товар", callback_data=f"a:paddprod:{cat_id}")])
    kb.append([InlineKeyboardButton(text="📥 Массовое добавление", callback_data=f"a:pbulk:{cat_id}")])
    kb.append([
        InlineKeyboardButton(text="🔙 Категории", callback_data="a:products"),
        InlineKeyboardButton(text="🏠 Главная", callback_data="a:home"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def kb_product_card(cat_id: int, product_id: int, is_active: int) -> InlineKeyboardMarkup:
    toggle_text = "⛔ Выключить" if int(is_active) == 1 else "✅ Включить"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle_text, callback_data=f"a:ptoggle:{cat_id}:{product_id}")],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data=f"a:pcat:{cat_id}"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="a:home"),
        ],
    ])


def kb_search_results(items: list[dict]) -> InlineKeyboardMarkup:
    kb = []
    for p in items:
        kb.append([InlineKeyboardButton(
            text=f"{p['name']} — {p['price']}",
            callback_data=f"a:pprod:{p['category_id']}:{p['id']}",
        )])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="a:products")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def kb_bulk_confirm(cat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Импортировать", callback_data=f"a:pbulk_confirm:{cat_id}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"a:pbulk_cancel:{cat_id}")],
    ])


async def _get_shop_id_for_admin(db: Database, user_id: int) -> int | None:
    shop_ids = await get_admin_shop_ids(db, user_id)
    return shop_ids[0] if shop_ids else None


@router.callback_query(F.data == "a:products")
async def products_root(cq: CallbackQuery, state: FSMContext, db: Database):
    if not await is_shop_admin(db, cq.from_user.id):
        await cq.answer("Нет доступа", show_alert=True)
        return
    await state.clear()

    shop_id = await _get_shop_id_for_admin(db, cq.from_user.id)
    if not shop_id:
        await cq.message.edit_text("Нет привязанного магазина.", reply_markup=kb_home())
        await cq.answer()
        return

    async with db.conn() as conn:
        cur = await conn.execute(
            "SELECT id, name, sort, is_active FROM categories WHERE shop_id=? ORDER BY sort, id",
            (shop_id,),
        )
        cats = [dict(r) for r in await cur.fetchall()]

    if not cats:
        await cq.message.edit_text(
            "🧺 Продукты\n\nКатегорий пока нет.\nНажми «➕ Добавить категорию».",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить категорию", callback_data="a:paddcat")],
                [InlineKeyboardButton(text="🏠 Главная", callback_data="a:home")],
            ])
        )
        await cq.answer()
        return

    await cq.message.edit_text("🧺 Категории:", reply_markup=kb_categories(cats))
    await cq.answer()


@router.callback_query(F.data == "a:psearch")
async def search_prompt(cq: CallbackQuery, state: FSMContext, db: Database):
    if not await is_shop_admin(db, cq.from_user.id):
        await cq.answer("Нет доступа", show_alert=True)
        return

    shop_id = await _get_shop_id_for_admin(db, cq.from_user.id)
    if not shop_id:
        await cq.message.edit_text("Нет привязанного магазина.", reply_markup=kb_home())
        await cq.answer()
        return

    await state.set_state(ProductStates.search)
    await state.update_data(shop_id=shop_id)
    await cq.message.edit_text("Введите запрос для поиска товара:", reply_markup=kb_home())
    await cq.answer()


@router.message(ProductStates.search)
async def search_products(message: Message, state: FSMContext, db: Database):
    if not await is_shop_admin(db, message.from_user.id):
        await message.answer("Нет доступа.")
        return

    data = await state.get_data()
    shop_id = data.get("shop_id")
    if not shop_id:
        await message.answer("Нет привязанного магазина.", reply_markup=kb_admin_main())
        await state.clear()
        return

    query = (message.text or "").strip()
    service = SearchService(db)
    results = await service.search_products(query, shop_id=int(shop_id), limit=10, active_only=False)

    if not results:
        await message.answer("Ничего не найдено. Попробуйте уточнить запрос.")
        return

    await message.answer("Результаты поиска:", reply_markup=kb_search_results(list(results)))


@router.callback_query(F.data == "a:paddcat")
async def add_category_prompt(cq: CallbackQuery, state: FSMContext, db: Database):
    if not await is_shop_admin(db, cq.from_user.id):
        await cq.answer("Нет доступа", show_alert=True)
        return

    await state.set_state(ProductStates.add_category)
    await cq.message.edit_text("Введите название категории (например: Овощи):", reply_markup=kb_home())
    await cq.answer()


@router.message(ProductStates.add_category)
async def add_category_save(message: Message, state: FSMContext, db: Database):
    if not await is_shop_admin(db, message.from_user.id):
        await message.answer("Нет доступа.")
        return

    shop_id = await _get_shop_id_for_admin(db, message.from_user.id)
    if not shop_id:
        await message.answer("Нет привязанного магазина.", reply_markup=kb_admin_main())
        await state.clear()
        return

    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Слишком коротко. Введите название категории ещё раз:")
        return

    async with db.conn() as conn:
        await conn.execute(
            "INSERT INTO categories(shop_id, name, name_norm, sort, is_active) VALUES(?,?,?,0,1)",
            (shop_id, name, normalize(name)),
        )
        await conn.commit()

    await state.clear()
    await message.answer("Категория добавлена ✅", reply_markup=kb_admin_main())


@router.callback_query(F.data.startswith("a:pcat:"))
async def open_category(cq: CallbackQuery, db: Database):
    if not await is_shop_admin(db, cq.from_user.id):
        await cq.answer("Нет доступа", show_alert=True)
        return

    shop_id = await _get_shop_id_for_admin(db, cq.from_user.id)
    if not shop_id:
        await cq.message.edit_text("Нет привязанного магазина.", reply_markup=kb_home())
        await cq.answer()
        return

    cat_id = int(cq.data.split(":")[2])

    repo = ProductsRepo(db)
    items = await repo.list_by_category_any(shop_id=shop_id, category_id=cat_id)

    title = f"🧺 Товары в категории #{cat_id}:"
    await cq.message.edit_text(title, reply_markup=kb_products(cat_id, items))
    await cq.answer()


@router.callback_query(F.data.startswith("a:paddprod:"))
async def add_product_prompt(cq: CallbackQuery, state: FSMContext, db: Database):
    if not await is_shop_admin(db, cq.from_user.id):
        await cq.answer("Нет доступа", show_alert=True)
        return

    cat_id = int(cq.data.split(":")[2])
    await state.set_state(ProductStates.add_product)
    await state.update_data(category_id=cat_id)
    await cq.message.edit_text(
        "Введите товар в формате:\n"
        "Название; Цена\n\n"
        "Пример:\n"
        "Молоко 2.5%; 12.5",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"a:pcat:{cat_id}")],
            [InlineKeyboardButton(text="🏠 Главная", callback_data="a:home")],
        ])
    )
    await cq.answer()


@router.callback_query(F.data.startswith("a:pbulk:"))
async def bulk_add_prompt(cq: CallbackQuery, state: FSMContext, db: Database):
    if not await is_shop_admin(db, cq.from_user.id):
        await cq.answer("Нет доступа", show_alert=True)
        return

    cat_id = int(cq.data.split(":")[2])
    shop_id = await _get_shop_id_for_admin(db, cq.from_user.id)
    if not shop_id:
        await cq.message.edit_text("Нет привязанного магазина.", reply_markup=kb_home())
        await cq.answer()
        return

    await state.set_state(ProductStates.bulk_upload)
    await state.update_data(category_id=cat_id, shop_id=shop_id)
    await cq.message.edit_text(
        "Загрузите CSV файл.\n"
        "Обязательные колонки: name, price.\n"
        "Опционально: description.\n"
        "Пример строки: Яблоки; 12.5; Сочные",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"a:pcat:{cat_id}")],
            [InlineKeyboardButton(text="🏠 Главная", callback_data="a:home")],
        ]),
    )
    await cq.answer()


@router.message(ProductStates.bulk_upload, F.document)
async def bulk_add_receive(message: Message, state: FSMContext, db: Database):
    if not await is_shop_admin(db, message.from_user.id):
        await message.answer("Нет доступа.")
        return

    if not message.document.file_name.lower().endswith(".csv"):
        await message.answer("Поддерживаются только CSV файлы.")
        return

    data = await state.get_data()
    cat_id = int(data.get("category_id", 0))
    shop_id = int(data.get("shop_id", 0))
    if not cat_id or not shop_id:
        await message.answer("Не удалось определить категорию.", reply_markup=kb_admin_main())
        await state.clear()
        return

    file = await message.bot.get_file(message.document.file_id)
    file_stream = await message.bot.download_file(file.file_path)
    content = BytesIO(file_stream.read()).getvalue().decode("utf-8", errors="replace")

    from app.services.import_service import parse_products_csv, preview_rows

    result = parse_products_csv(content)
    if result.errors:
        await message.answer("Ошибки в файле:\n" + "\n".join(f"- {e}" for e in result.errors))
        return

    existing = ProductsRepo(db)
    current_items = await existing.list_by_category_any(shop_id=shop_id, category_id=cat_id)
    existing_names = {normalize(p["name"]) for p in current_items}
    duplicates = [r for r in result.rows if normalize(r.name) in existing_names]
    if duplicates:
        names = ", ".join({d.name for d in duplicates})
        await message.answer(f"В категории уже есть товары: {names}. Уберите дубликаты.")
        return

    preview = preview_rows(result.rows, limit=5)
    preview_text = "\n".join(preview) if preview else "Нет строк для предпросмотра."
    await state.set_state(ProductStates.bulk_confirm)
    await state.update_data(rows=[r.__dict__ for r in result.rows])
    await message.answer(
        "Предпросмотр первых строк:\n"
        f"{preview_text}\n\n"
        f"Всего к импорту: {len(result.rows)}",
        reply_markup=kb_bulk_confirm(cat_id),
    )


@router.callback_query(F.data.startswith("a:pbulk_confirm:"))
async def bulk_add_confirm(cq: CallbackQuery, state: FSMContext, db: Database):
    if not await is_shop_admin(db, cq.from_user.id):
        await cq.answer("Нет доступа", show_alert=True)
        return

    data = await state.get_data()
    cat_id = int(data.get("category_id", 0))
    shop_id = int(data.get("shop_id", 0))
    rows = data.get("rows", [])
    if not rows:
        await cq.message.edit_text("Нет данных для импорта.", reply_markup=kb_admin_main())
        await state.clear()
        await cq.answer()
        return

    repo = ProductsRepo(db)
    for row in rows:
        await repo.create(
            shop_id=shop_id,
            category_id=cat_id,
            name=row["name"],
            price=float(row["price"]),
            description=row.get("description", "") or None,
        )

    await state.clear()
    await cq.message.edit_text(f"Импортировано товаров: {len(rows)} ✅", reply_markup=kb_admin_main())
    await cq.answer()


@router.callback_query(F.data.startswith("a:pbulk_cancel:"))
async def bulk_add_cancel(cq: CallbackQuery, state: FSMContext, db: Database):
    if not await is_shop_admin(db, cq.from_user.id):
        await cq.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await cq.message.edit_text("Импорт отменён.", reply_markup=kb_admin_main())
    await cq.answer()


@router.message(ProductStates.add_product)
async def add_product_save(message: Message, state: FSMContext, db: Database):
    if not await is_shop_admin(db, message.from_user.id):
        await message.answer("Нет доступа.")
        return

    shop_id = await _get_shop_id_for_admin(db, message.from_user.id)
    if not shop_id:
        await message.answer("Нет привязанного магазина.", reply_markup=kb_admin_main())
        await state.clear()
        return

    data = await state.get_data()
    cat_id = int(data["category_id"])

    text = (message.text or "").strip()
    if ";" not in text:
        await message.answer("Неверный формат. Нужно: Название; Цена\nПример: Хлеб; 7")
        return

    name, price_str = [x.strip() for x in text.split(";", 1)]
    try:
        price = float(price_str.replace(",", "."))
    except ValueError:
        await message.answer("Цена должна быть числом. Пример: 12.5")
        return

    repo = ProductsRepo(db)
    await repo.create(shop_id=shop_id, category_id=cat_id, name=name, price=price)

    await state.clear()
    await message.answer("Товар добавлен ✅", reply_markup=kb_admin_main())


@router.callback_query(F.data.startswith("a:pprod:"))
async def product_card(cq: CallbackQuery, db: Database):
    if not await is_shop_admin(db, cq.from_user.id):
        await cq.answer("Нет доступа", show_alert=True)
        return

    _, _, cat_id_s, prod_id_s = cq.data.split(":")
    cat_id = int(cat_id_s)
    product_id = int(prod_id_s)

    repo = ProductsRepo(db)
    p = await repo.get(product_id)
    if not p:
        await cq.message.edit_text("Товар не найден.", reply_markup=kb_home())
        await cq.answer()
        return

    text = (
        f"📦 {p['name']}\n"
        f"Цена: {p['price']}\n"
        f"Статус: {'✅ Активен' if int(p['is_active'])==1 else '⛔ Выключен'}\n"
    )
    await cq.message.edit_text(text, reply_markup=kb_product_card(cat_id, product_id, p["is_active"]))
    await cq.answer()


@router.callback_query(F.data.startswith("a:ptoggle:"))
async def toggle_product(cq: CallbackQuery, db: Database):
    if not await is_shop_admin(db, cq.from_user.id):
        await cq.answer("Нет доступа", show_alert=True)
        return

    _, _, cat_id_s, prod_id_s = cq.data.split(":")
    cat_id = int(cat_id_s)
    product_id = int(prod_id_s)

    shop_id = await _get_shop_id_for_admin(db, cq.from_user.id)
    if not shop_id:
        await cq.answer("Нет магазина", show_alert=True)
        return

    repo = ProductsRepo(db)
    new_state = await repo.toggle_active(shop_id=shop_id, product_id=product_id)
    if new_state is None:
        await cq.answer("Товар не найден", show_alert=True)
        return

    await cq.answer("Готово ✅")
    # перерисуем карточку
    p = await repo.get(product_id)
    text = (
        f"📦 {p['name']}\n"
        f"Цена: {p['price']}\n"
        f"Статус: {'✅ Активен' if int(p['is_active'])==1 else '⛔ Выключен'}\n"
    )
    await cq.message.edit_text(text, reply_markup=kb_product_card(cat_id, product_id, p["is_active"]))
