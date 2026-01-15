from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.ui.nav import kb_nav


def kb_client_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Магазины", callback_data="c:shops")],
        [InlineKeyboardButton(text="🍽 Рестораны", callback_data="c:restaurants")],
        [InlineKeyboardButton(text="🧺 Корзина", callback_data="c:cart")],
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
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="c:back:main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def kb_categories_list(categories: list[dict], kind: str, shop_id: int) -> InlineKeyboardMarkup:
    """
    callback: c:cat:{shop_id}:{category_id}
    """
    kb = []
    for c in categories:
        kb.append([InlineKeyboardButton(text=c["name"], callback_data=f"c:cat:{shop_id}:{c['id']}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"c:back:{kind}_list")])
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


def kb_cart(items: list[dict]) -> InlineKeyboardMarkup:
    """
    items: [{'product_id','quantity','name','price','shop_id'}, ...]
    callback:
      c:cart_dec:{product_id}
      c:cart_inc:{product_id}
      c:cart_del:{product_id}
      c:checkout
      c:back:main
    """
    kb = []
    for it in items:
        pid = it["product_id"]
        kb.append([
            InlineKeyboardButton(text="➖", callback_data=f"c:cart_dec:{pid}"),
            InlineKeyboardButton(text=f"{it['quantity']} шт", callback_data="c:noop"),
            InlineKeyboardButton(text="➕", callback_data=f"c:cart_inc:{pid}"),
        ])
        kb.append([
            InlineKeyboardButton(text=f"❌ Удалить {it['name']}", callback_data=f"c:cart_del:{pid}")
        ])

    kb.append([InlineKeyboardButton(text="🧾 Оформить заказ", callback_data="c:checkout")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="c:back:main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def kb_checkout_choose_shop(shop_ids: list[int]) -> InlineKeyboardMarkup:
    """
    Если в корзине товары из разных точек, даём выбрать, для какого shop_id оформить заказ.
    callback: c:checkout_shop:{shop_id}
    """
    kb = []
    for sid in shop_ids:
        kb.append([InlineKeyboardButton(text=f"Оформить для точки ID {sid}", callback_data=f"c:checkout_shop:{sid}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="c:cart")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def kb_after_order() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="c:back:main")]
    ])
