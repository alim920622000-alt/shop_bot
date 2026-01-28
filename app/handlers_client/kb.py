from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.ui.nav import kb_nav


def kb_client_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Заказать", callback_data="c:order")],
        [InlineKeyboardButton(text="📦 Заказы", callback_data="c:orders")],
        [InlineKeyboardButton(text="💬 Чат", callback_data="c:chat")],
        [InlineKeyboardButton(text="👤 Кабинет", callback_data="c:cabinet")],
    ])


def kb_client_order_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Магазины", callback_data="c:shops")],
        [InlineKeyboardButton(text="🍽 Рестораны", callback_data="c:restaurants")],
        [InlineKeyboardButton(text="🧺 Корзина", callback_data="c:cart:choose")],
        [InlineKeyboardButton(text="🕓 История", callback_data="c:history")],
        [InlineKeyboardButton(text="🔎 Поиск", callback_data="c:search:choose")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="c:home")],
    ])


def kb_back(to: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"c:back:{to}")]
    ])


def kb_shops_list(items: list[dict], kind: str) -> InlineKeyboardMarkup:
    """
    kind: 'shop' | 'restaurant'
    callback: c:pick:{kind}:{shop_id}
    """
    kb = []
    for x in items:
        kb.append([InlineKeyboardButton(text=x["name"], callback_data=f"c:pick:{kind}:{x['id']}")])
    cart_cb = "c:cart:shop" if kind == "shop" else "c:cart:restaurant"
    kb.append([
        InlineKeyboardButton(text="🏠 Домой", callback_data="c:home"),
        InlineKeyboardButton(text="🧺 Корзина", callback_data=cart_cb),
        InlineKeyboardButton(text="🔙 Назад", callback_data="c:order"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def kb_categories_list(categories: list[dict], kind: str, shop_id: int) -> InlineKeyboardMarkup:
    """
    callback: c:cat:{shop_id}:{category_id}
    """
    kb = []
    for c in categories:
        kb.append([InlineKeyboardButton(text=c["name"], callback_data=f"c:cat:{shop_id}:{c['id']}")])
    back_cb = "c:shops" if kind == "shop" else "c:restaurants"
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def kb_products_list(products: list[dict], shop_id: int, category_id: int) -> InlineKeyboardMarkup:
    """
    callback: c:prod:{product_id}
    """
    kb = []
    for p in products:
        price = p["price"]
        kb.append([InlineKeyboardButton(
            text=f"{p['name']} — {price}",
            callback_data=f"c:prod:{p['id']}"
        )])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"c:pickback:{shop_id}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def kb_product_card(product_id: int, shop_id: int, category_id: int) -> InlineKeyboardMarkup:
    """
    callback:
      c:add:{product_id} — добавить в корзину
      c:cat:{shop_id}:{category_id} — назад в товары категории
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить в корзину", callback_data=f"c:add:{product_id}")],
        [
            InlineKeyboardButton(text="🏠 Главная", callback_data="c:home"),
            InlineKeyboardButton(text="🔙 Назад", callback_data=f"c:cat:{shop_id}:{category_id}"),
        ],
    ])


def kb_cart(items: list[dict], business_type: str) -> InlineKeyboardMarkup:
    """
    items: [{'product_id','quantity','name','price','shop_id'}, ...]
    callback:
      c:cart_dec:{business_type}:{product_id}
      c:cart_inc:{business_type}:{product_id}
      c:cart_del:{business_type}:{product_id}
      c:checkout:{business_type}
      c:home
    """
    kb = []
    for it in items:
        pid = it["product_id"]
        kb.append([
            InlineKeyboardButton(text="➖", callback_data=f"c:cart_dec:{business_type}:{pid}"),
            InlineKeyboardButton(text=f"{it['quantity']} шт", callback_data="c:noop"),
            InlineKeyboardButton(text="➕", callback_data=f"c:cart_inc:{business_type}:{pid}"),
        ])
        kb.append([
            InlineKeyboardButton(text=f"❌ Удалить {it['name']}", callback_data=f"c:cart_del:{business_type}:{pid}")
        ])

    kb.append([InlineKeyboardButton(text="🧾 Оформить заказ", callback_data=f"c:checkout:{business_type}")])
    kb.append([
        InlineKeyboardButton(text="🏠 Домой", callback_data="c:home"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="c:order"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def kb_checkout_choose_shop(shop_ids: list[int], business_type: str) -> InlineKeyboardMarkup:
    """
    Если в корзине товары из разных точек, даём выбрать, для какого shop_id оформить заказ.
    callback: c:checkout_shop:{shop_id}
    """
    kb = []
    for sid in shop_ids:
        kb.append([InlineKeyboardButton(
            text=f"Оформить для точки ID {sid}",
            callback_data=f"c:checkout_shop:{business_type}:{sid}",
        )])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"c:cart:{business_type}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def kb_after_order() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="c:back:main")]
    ])


def kb_cart_choose() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Корзина магазинов", callback_data="c:cart:shop")],
        [InlineKeyboardButton(text="🍽 Корзина ресторанов", callback_data="c:cart:restaurant")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="c:order")],
    ])


def kb_search_choose() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 По товарам магазинов", callback_data="c:search:shop")],
        [InlineKeyboardButton(text="🔎 По меню ресторанов", callback_data="c:search:restaurant")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="c:order")],
    ])


def kb_orders_list(order_ids: list[int], prefix: str) -> InlineKeyboardMarkup:
    kb = []
    for oid in order_ids:
        kb.append([InlineKeyboardButton(text=f"Заказ #{oid}", callback_data=f"{prefix}:{oid}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="c:home")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def kb_chat_list(order_ids: list[int], prefix: str) -> InlineKeyboardMarkup:
    kb = []
    for oid in order_ids:
        kb.append([InlineKeyboardButton(text=f"Чат по заказу #{oid}", callback_data=f"{prefix}:{oid}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="c:home")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def kb_order_card(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Чат по заказу", callback_data=f"c:chat:order:{order_id}")],
        [InlineKeyboardButton(text="🏠 Домой", callback_data="c:home")],
    ])


def kb_cabinet() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить ФИО", callback_data="c:cabinet:edit:full_name")],
        [InlineKeyboardButton(text="📞 Изменить телефон", callback_data="c:cabinet:edit:phone")],
        [InlineKeyboardButton(text="🏠 Изменить адрес", callback_data="c:cabinet:edit:address")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="c:home")],
    ])


def kb_chat_order() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="c:chat")],
        [InlineKeyboardButton(text="🏠 Домой", callback_data="c:home")],
    ])
