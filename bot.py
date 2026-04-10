import os
import json
import logging
import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# КОНФИГУРАЦИЯ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BOT_TOKEN = "8674017448:AAF0DE0OQMVFzGCGSKYV1P30Rfezd-LGTN0"
ADMIN_IDS = []  # Заполнится автоматически первым /admin
ORDER_CONTACT = "@sulik"
SHOP_NAME = "HAMASHA"
DATA_DIR = "data"
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
CATEGORIES_FILE = os.path.join(DATA_DIR, "categories.json")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
ADMINS_FILE = os.path.join(DATA_DIR, "admins.json")
CART_FILE = os.path.join(DATA_DIR, "carts.json")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ДАННЫЕ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def load_json(path, default=None):
    if default is None:
        default = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save_json(path, data):
    ensure_data_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_products():
    return load_json(PRODUCTS_FILE, [])

def save_products(products):
    save_json(PRODUCTS_FILE, products)

def get_categories():
    return load_json(CATEGORIES_FILE, [])

def save_categories(cats):
    save_json(CATEGORIES_FILE, cats)

def get_orders():
    return load_json(ORDERS_FILE, [])

def save_orders(orders):
    save_json(ORDERS_FILE, orders)

def get_admins():
    return load_json(ADMINS_FILE, [])

def save_admins(admins):
    save_json(ADMINS_FILE, admins)

def get_carts():
    return load_json(CART_FILE, {})

def save_carts(carts):
    save_json(CART_FILE, carts)

def get_cart(user_id):
    carts = get_carts()
    return carts.get(str(user_id), [])

def save_cart(user_id, cart):
    carts = get_carts()
    carts[str(user_id)] = cart
    save_carts(carts)

def clear_cart(user_id):
    carts = get_carts()
    carts.pop(str(user_id), None)
    save_carts(carts)

def is_admin(user_id):
    admins = get_admins()
    return user_id in admins

def next_product_id():
    products = get_products()
    return max([p.get("id", 0) for p in products], default=0) + 1

def next_order_id():
    orders = get_orders()
    return max([o.get("id", 0) for o in orders], default=0) + 1

def fmt_price(price):
    return f"{price:,.0f}".replace(",", " ") + " ₽"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# КЛИЕНТСКАЯ ЧАСТЬ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def start(update: Update, context):
    text = (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"     {SHOP_NAME}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Добро пожаловать!\n"
        f"Стильная одежда для тех,\n"
        f"кто ценит качество.\n\n"
        f"Выберите раздел:"
    )
    kb = [
        [InlineKeyboardButton("🛍  КАТАЛОГ", callback_data="catalog")],
        [InlineKeyboardButton("🛒  КОРЗИНА", callback_data="cart")],
        [InlineKeyboardButton("📦  МОИ ЗАКАЗЫ", callback_data="my_orders")],
        [InlineKeyboardButton("📞  СВЯЗАТЬСЯ", callback_data="contact")],
        [InlineKeyboardButton("ℹ️  КАК ЗАКАЗАТЬ", callback_data="how_to")],
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))

async def catalog_menu(update: Update, context):
    q = update.callback_query
    await q.answer()
    categories = get_categories()
    products = get_products()
    if not products:
        await q.edit_message_text(
            "Каталог пока пуст.\nЗагляните позже!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀ НАЗАД", callback_data="home")]])
        )
        return
    kb = []
    if categories:
        for cat in categories:
            count = len([p for p in products if p.get("category") == cat["name"] and p.get("visible", True)])
            if count > 0:
                kb.append([InlineKeyboardButton(f"{cat.get('emoji','📂')}  {cat['name'].upper()}  ({count})", callback_data=f"cat_{cat['name']}")])
    # товары без категории
    no_cat = [p for p in products if not p.get("category") and p.get("visible", True)]
    if no_cat:
        kb.append([InlineKeyboardButton(f"📂  ВСЕ ТОВАРЫ  ({len(no_cat)})", callback_data="cat_")])
    # если нет категорий — показать все
    if not categories:
        visible = [p for p in products if p.get("visible", True)]
        kb = []
        for p in visible:
            kb.append([InlineKeyboardButton(f"{p['name']}  —  {fmt_price(p['price'])}", callback_data=f"prod_{p['id']}")])
    kb.append([InlineKeyboardButton("◀ НАЗАД", callback_data="home")])
    await q.edit_message_text(
        f"━━━━━━━━━━━━━━━━━━━━━━\n     КАТАЛОГ\n━━━━━━━━━━━━━━━━━━━━━━",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def category_products(update: Update, context):
    q = update.callback_query
    await q.answer()
    cat_name = q.data[4:]  # после "cat_"
    products = get_products()
    if cat_name:
        items = [p for p in products if p.get("category") == cat_name and p.get("visible", True)]
        title = cat_name.upper()
    else:
        items = [p for p in products if not p.get("category") and p.get("visible", True)]
        title = "ВСЕ ТОВАРЫ"
    kb = []
    for p in items:
        kb.append([InlineKeyboardButton(f"{p['name']}  —  {fmt_price(p['price'])}", callback_data=f"prod_{p['id']}")])
    kb.append([InlineKeyboardButton("◀ К КАТАЛОГУ", callback_data="catalog")])
    await q.edit_message_text(
        f"━━━━━━━━━━━━━━━━━━━━━━\n     {title}\n━━━━━━━━━━━━━━━━━━━━━━",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def product_card(update: Update, context):
    q = update.callback_query
    await q.answer()
    prod_id = int(q.data.split("_")[1])
    products = get_products()
    product = next((p for p in products if p["id"] == prod_id), None)
    if not product:
        await q.edit_message_text("Товар не найден.")
        return
    text = (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  {product['name'].upper()}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    if product.get("description"):
        text += f"{product['description']}\n\n"
    if product.get("sizes"):
        text += f"📐 Размеры: {product['sizes']}\n"
    if product.get("colors"):
        text += f"🎨 Цвета: {product['colors']}\n"
    text += f"\n💰 Цена: {fmt_price(product['price'])}\n"
    if product.get("old_price"):
        text += f"~~{fmt_price(product['old_price'])}~~\n"

    kb = [
        [InlineKeyboardButton("🛒  В КОРЗИНУ", callback_data=f"addcart_{prod_id}")],
        [InlineKeyboardButton("⚡  КУПИТЬ СЕЙЧАС", callback_data=f"buynow_{prod_id}")],
        [InlineKeyboardButton("◀ НАЗАД", callback_data="catalog")],
    ]

    # Удаляем старое сообщение и отправляем новое (чтобы фото показать)
    try:
        await q.message.delete()
    except:
        pass

    if product.get("photo"):
        await context.bot.send_photo(
            chat_id=q.message.chat_id,
            photo=product["photo"],
            caption=text,
            reply_markup=InlineKeyboardMarkup(kb)
        )
    else:
        await context.bot.send_message(
            chat_id=q.message.chat_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(kb)
        )

async def add_to_cart(update: Update, context):
    q = update.callback_query
    prod_id = int(q.data.split("_")[1])
    user_id = q.from_user.id
    cart = get_cart(user_id)
    # Проверяем есть ли уже
    found = False
    for item in cart:
        if item["product_id"] == prod_id:
            item["qty"] += 1
            found = True
            break
    if not found:
        cart.append({"product_id": prod_id, "qty": 1})
    save_cart(user_id, cart)
    await q.answer("✓ Добавлено в корзину!", show_alert=False)

async def cart_view(update: Update, context):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    cart = get_cart(user_id)
    products = get_products()

    if not cart:
        kb = [[InlineKeyboardButton("🛍  В КАТАЛОГ", callback_data="catalog")],
              [InlineKeyboardButton("◀ НАЗАД", callback_data="home")]]
        try:
            await q.edit_message_text("Корзина пуста.", reply_markup=InlineKeyboardMarkup(kb))
        except:
            await q.message.reply_text("Корзина пуста.", reply_markup=InlineKeyboardMarkup(kb))
        return

    text = "━━━━━━━━━━━━━━━━━━━━━━\n     КОРЗИНА\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    total = 0
    kb = []
    for item in cart:
        p = next((x for x in products if x["id"] == item["product_id"]), None)
        if not p:
            continue
        line_total = p["price"] * item["qty"]
        total += line_total
        text += f"▸ {p['name']}  ×{item['qty']}  —  {fmt_price(line_total)}\n"
        kb.append([
            InlineKeyboardButton("−", callback_data=f"cartminus_{item['product_id']}"),
            InlineKeyboardButton(f"{item['qty']} шт.", callback_data="noop"),
            InlineKeyboardButton("+", callback_data=f"cartplus_{item['product_id']}"),
        ])
    text += f"\n━━━━━━━━━━━━━━━━━━━━━━\nИТОГО: {fmt_price(total)}\n━━━━━━━━━━━━━━━━━━━━━━"
    kb.append([InlineKeyboardButton("📦  ОФОРМИТЬ ЗАКАЗ", callback_data="checkout")])
    kb.append([InlineKeyboardButton("🗑  ОЧИСТИТЬ", callback_data="cart_clear")])
    kb.append([InlineKeyboardButton("◀ НАЗАД", callback_data="home")])
    try:
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    except:
        await q.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))

async def cart_adjust(update: Update, context):
    q = update.callback_query
    user_id = q.from_user.id
    action, pid = q.data.split("_", 1)
    pid = int(pid)
    cart = get_cart(user_id)
    for item in cart:
        if item["product_id"] == pid:
            if action == "cartplus":
                item["qty"] += 1
            elif action == "cartminus":
                item["qty"] -= 1
                if item["qty"] <= 0:
                    cart.remove(item)
            break
    save_cart(user_id, cart)
    # Переотрисовываем корзину
    q.data = "cart"
    await cart_view(update, context)

async def cart_clear(update: Update, context):
    q = update.callback_query
    clear_cart(q.from_user.id)
    await q.answer("Корзина очищена")
    q.data = "cart"
    await cart_view(update, context)

# ━━━ ОФОРМЛЕНИЕ ЗАКАЗА ━━━
CHECKOUT_NAME, CHECKOUT_PHONE, CHECKOUT_ADDRESS, CHECKOUT_COMMENT = range(4)

async def checkout_start(update: Update, context):
    q = update.callback_query
    await q.answer()
    cart = get_cart(q.from_user.id)
    if not cart:
        await q.edit_message_text("Корзина пуста.")
        return
    await q.edit_message_text(
        "━━━━━━━━━━━━━━━━━━━━━━\n     ОФОРМЛЕНИЕ ЗАКАЗА\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Введите ваше имя:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✕ ОТМЕНА", callback_data="cart")]])
    )
    context.user_data["checkout"] = {"user_id": q.from_user.id, "username": q.from_user.username}
    return CHECKOUT_NAME

async def checkout_name(update: Update, context):
    context.user_data["checkout"]["name"] = update.message.text
    await update.message.reply_text("📱 Введите номер телефона:")
    return CHECKOUT_PHONE

async def checkout_phone(update: Update, context):
    context.user_data["checkout"]["phone"] = update.message.text
    await update.message.reply_text("📍 Введите адрес доставки\n(или напишите «самовывоз»):")
    return CHECKOUT_ADDRESS

async def checkout_address(update: Update, context):
    context.user_data["checkout"]["address"] = update.message.text
    await update.message.reply_text("💬 Комментарий к заказу\n(или напишите «нет»):")
    return CHECKOUT_COMMENT

async def checkout_finish(update: Update, context):
    info = context.user_data.get("checkout", {})
    info["comment"] = update.message.text
    user_id = info["user_id"]
    cart = get_cart(user_id)
    products = get_products()

    order_id = next_order_id()
    items = []
    total = 0
    for ci in cart:
        p = next((x for x in products if x["id"] == ci["product_id"]), None)
        if not p:
            continue
        items.append({"name": p["name"], "price": p["price"], "qty": ci["qty"]})
        total += p["price"] * ci["qty"]

    order = {
        "id": order_id,
        "user_id": user_id,
        "username": info.get("username", ""),
        "name": info.get("name", ""),
        "phone": info.get("phone", ""),
        "address": info.get("address", ""),
        "comment": info.get("comment", ""),
        "items": items,
        "total": total,
        "status": "new",
        "created": datetime.datetime.now().isoformat(),
    }
    orders = get_orders()
    orders.append(order)
    save_orders(orders)
    clear_cart(user_id)

    # Сообщение клиенту
    text = (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  ✅  ЗАКАЗ #{order_id} ПРИНЯТ\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    for it in items:
        text += f"▸ {it['name']}  ×{it['qty']}  —  {fmt_price(it['price'] * it['qty'])}\n"
    text += (
        f"\nИтого: {fmt_price(total)}\n\n"
        f"Имя: {info['name']}\n"
        f"Тел: {info['phone']}\n"
        f"Адрес: {info['address']}\n\n"
        f"Мы свяжемся с вами\nдля подтверждения!"
    )
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀ НА ГЛАВНУЮ", callback_data="home")]])
    )

    # Уведомление админам
    admin_text = (
        f"🔔 НОВЫЙ ЗАКАЗ #{order_id}\n\n"
        f"Клиент: {info['name']}\n"
        f"Тел: {info['phone']}\n"
        f"Адрес: {info['address']}\n"
        f"Комментарий: {info.get('comment','—')}\n"
        f"Username: @{info.get('username','—')}\n\n"
    )
    for it in items:
        admin_text += f"▸ {it['name']} ×{it['qty']} — {fmt_price(it['price']*it['qty'])}\n"
    admin_text += f"\nИТОГО: {fmt_price(total)}"

    admin_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить", callback_data=f"ordstatus_{order_id}_confirmed")],
        [InlineKeyboardButton("🚚 Отправлен", callback_data=f"ordstatus_{order_id}_shipped")],
        [InlineKeyboardButton("❌ Отклонить", callback_data=f"ordstatus_{order_id}_cancelled")],
    ])
    for aid in get_admins():
        try:
            await context.bot.send_message(chat_id=aid, text=admin_text, reply_markup=admin_kb)
        except:
            pass

    return ConversationHandler.END

async def checkout_cancel(update: Update, context):
    if update.callback_query:
        await update.callback_query.answer()
    return ConversationHandler.END

# ━━━ БЫСТРАЯ ПОКУПКА ━━━
async def buy_now(update: Update, context):
    q = update.callback_query
    prod_id = int(q.data.split("_")[1])
    user_id = q.from_user.id
    # Очищаем корзину и добавляем только этот товар
    save_cart(user_id, [{"product_id": prod_id, "qty": 1}])
    # Начинаем чекаут
    await checkout_start(update, context)
    return CHECKOUT_NAME

async def my_orders(update: Update, context):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    orders = get_orders()
    user_orders = [o for o in orders if o["user_id"] == user_id]
    if not user_orders:
        await q.edit_message_text(
            "У вас пока нет заказов.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀ НАЗАД", callback_data="home")]])
        )
        return
    status_map = {"new": "🆕 Новый", "confirmed": "✅ Подтверждён", "shipped": "🚚 Отправлен",
                  "delivered": "📦 Доставлен", "cancelled": "❌ Отменён"}
    text = "━━━━━━━━━━━━━━━━━━━━━━\n     МОИ ЗАКАЗЫ\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for o in user_orders[-10:]:
        st = status_map.get(o["status"], o["status"])
        text += f"Заказ #{o['id']}  —  {fmt_price(o['total'])}\nСтатус: {st}\n\n"
    await q.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀ НАЗАД", callback_data="home")]])
    )

async def contact_view(update: Update, context):
    q = update.callback_query
    await q.answer()
    text = (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"     СВЯЗАТЬСЯ С НАМИ\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Менеджер: {ORDER_CONTACT}\n\n"
        f"Мы ответим в ближайшее время!"
    )
    await q.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💬  НАПИСАТЬ", url=f"https://t.me/{ORDER_CONTACT.lstrip('@')}")],
            [InlineKeyboardButton("◀ НАЗАД", callback_data="home")],
        ])
    )

async def how_to_view(update: Update, context):
    q = update.callback_query
    await q.answer()
    text = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "     КАК ЗАКАЗАТЬ\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "1️⃣  Выберите товары в каталоге\n"
        "2️⃣  Добавьте в корзину\n"
        "3️⃣  Нажмите «Оформить заказ»\n"
        "4️⃣  Заполните контактные данные\n"
        "5️⃣  Мы свяжемся для подтверждения\n\n"
        "Оплата при получении.\n"
        "Доставка по городу — бесплатно!"
    )
    await q.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀ НАЗАД", callback_data="home")]])
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# АДМИН-ПАНЕЛЬ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def admin_cmd(update: Update, context):
    user_id = update.effective_user.id
    admins = get_admins()
    if not admins:
        admins.append(user_id)
        save_admins(admins)
    if user_id not in admins:
        await update.message.reply_text("⛔ Нет доступа.")
        return
    await show_admin_menu(update.message, context)

async def show_admin_menu(message, context):
    products = get_products()
    orders = get_orders()
    new_orders = len([o for o in orders if o["status"] == "new"])
    text = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "     АДМИН-ПАНЕЛЬ\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Товаров: {len(products)}\n"
        f"Заказов: {len(orders)}  (новых: {new_orders})\n"
    )
    kb = [
        [InlineKeyboardButton("➕ ДОБАВИТЬ ТОВАР", callback_data="adm_addprod")],
        [InlineKeyboardButton("📋 ТОВАРЫ", callback_data="adm_products")],
        [InlineKeyboardButton("📂 КАТЕГОРИИ", callback_data="adm_categories")],
        [InlineKeyboardButton("📦 ЗАКАЗЫ", callback_data="adm_orders")],
        [InlineKeyboardButton("📊 СТАТИСТИКА", callback_data="adm_stats")],
        [InlineKeyboardButton("📢 РАССЫЛКА", callback_data="adm_broadcast")],
    ]
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))

# ━━━ УПРАВЛЕНИЕ ТОВАРАМИ ━━━
(ADM_NAME, ADM_PRICE, ADM_DESC, ADM_SIZES, ADM_COLORS, ADM_CATEGORY, ADM_PHOTO,
 ADM_EDIT_FIELD, ADM_EDIT_VALUE,
 ADM_CAT_NAME, ADM_CAT_EMOJI,
 ADM_BROADCAST_TEXT) = range(12)

async def adm_addprod_start(update: Update, context):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("Нет доступа"); return ConversationHandler.END
    await q.answer()
    await q.edit_message_text("Введите название товара:")
    return ADM_NAME

async def adm_addprod_name(update: Update, context):
    context.user_data["new_prod"] = {"name": update.message.text}
    await update.message.reply_text("Введите цену (число):")
    return ADM_PRICE

async def adm_addprod_price(update: Update, context):
    try:
        price = int(update.message.text.replace(" ", "").replace("₽", ""))
    except ValueError:
        await update.message.reply_text("Введите число:")
        return ADM_PRICE
    context.user_data["new_prod"]["price"] = price
    await update.message.reply_text("Описание товара (или «нет»):")
    return ADM_DESC

async def adm_addprod_desc(update: Update, context):
    text = update.message.text
    if text.lower() not in ("нет", "-", ""):
        context.user_data["new_prod"]["description"] = text
    await update.message.reply_text("Размеры (напр. S, M, L, XL) или «нет»:")
    return ADM_SIZES

async def adm_addprod_sizes(update: Update, context):
    text = update.message.text
    if text.lower() not in ("нет", "-", ""):
        context.user_data["new_prod"]["sizes"] = text
    await update.message.reply_text("Цвета (напр. чёрный, белый) или «нет»:")
    return ADM_COLORS

async def adm_addprod_colors(update: Update, context):
    text = update.message.text
    if text.lower() not in ("нет", "-", ""):
        context.user_data["new_prod"]["colors"] = text
    categories = get_categories()
    if categories:
        kb = [[InlineKeyboardButton(c["name"], callback_data=f"setcat_{c['name']}")] for c in categories]
        kb.append([InlineKeyboardButton("Без категории", callback_data="setcat_")])
        await update.message.reply_text("Выберите категорию:", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text("Отправьте фото товара или «нет»:")
    return ADM_CATEGORY

async def adm_addprod_category(update: Update, context):
    if update.callback_query:
        q = update.callback_query
        await q.answer()
        cat = q.data[7:]  # после "setcat_"
        if cat:
            context.user_data["new_prod"]["category"] = cat
        await q.edit_message_text("Отправьте фото товара или напишите «нет»:")
    else:
        text = update.message.text
        if text.lower() not in ("нет", "-", ""):
            context.user_data["new_prod"]["category"] = text
        await update.message.reply_text("Отправьте фото товара или напишите «нет»:")
    return ADM_PHOTO

async def adm_addprod_photo(update: Update, context):
    new = context.user_data["new_prod"]
    if update.message.photo:
        new["photo"] = update.message.photo[-1].file_id
    new["id"] = next_product_id()
    new["visible"] = True
    products = get_products()
    products.append(new)
    save_products(products)
    await update.message.reply_text(
        f"✅ Товар «{new['name']}» добавлен!\nID: {new['id']}  Цена: {fmt_price(new['price'])}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀ АДМИН", callback_data="adm_home")]])
    )
    return ConversationHandler.END

async def adm_products_list(update: Update, context):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("Нет доступа"); return
    await q.answer()
    products = get_products()
    if not products:
        await q.edit_message_text("Нет товаров.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀ АДМИН", callback_data="adm_home")]]))
        return
    kb = []
    for p in products:
        vis = "👁" if p.get("visible", True) else "🚫"
        kb.append([InlineKeyboardButton(f"{vis} {p['name']} — {fmt_price(p['price'])}", callback_data=f"admprod_{p['id']}")])
    kb.append([InlineKeyboardButton("◀ АДМИН", callback_data="adm_home")])
    await q.edit_message_text("ТОВАРЫ:", reply_markup=InlineKeyboardMarkup(kb))

async def adm_product_detail(update: Update, context):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("Нет доступа"); return
    await q.answer()
    pid = int(q.data.split("_")[1])
    products = get_products()
    p = next((x for x in products if x["id"] == pid), None)
    if not p:
        await q.edit_message_text("Не найден."); return
    vis = "Виден" if p.get("visible", True) else "Скрыт"
    text = (
        f"ID: {p['id']}\n"
        f"Название: {p['name']}\n"
        f"Цена: {fmt_price(p['price'])}\n"
        f"Описание: {p.get('description','—')}\n"
        f"Размеры: {p.get('sizes','—')}\n"
        f"Цвета: {p.get('colors','—')}\n"
        f"Категория: {p.get('category','—')}\n"
        f"Фото: {'есть' if p.get('photo') else 'нет'}\n"
        f"Статус: {vis}"
    )
    toggle = "🚫 Скрыть" if p.get("visible", True) else "👁 Показать"
    kb = [
        [InlineKeyboardButton("✏️ Редактировать", callback_data=f"admedit_{pid}")],
        [InlineKeyboardButton(toggle, callback_data=f"admtoggle_{pid}")],
        [InlineKeyboardButton("📸 Заменить фото", callback_data=f"admphoto_{pid}")],
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"admdel_{pid}")],
        [InlineKeyboardButton("◀ К СПИСКУ", callback_data="adm_products")],
    ]
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

async def adm_toggle_visible(update: Update, context):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("Нет доступа"); return
    pid = int(q.data.split("_")[1])
    products = get_products()
    for p in products:
        if p["id"] == pid:
            p["visible"] = not p.get("visible", True)
            break
    save_products(products)
    await q.answer("Обновлено")
    q.data = f"admprod_{pid}"
    await adm_product_detail(update, context)

async def adm_delete_product(update: Update, context):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("Нет доступа"); return
    pid = int(q.data.split("_")[1])
    products = get_products()
    products = [p for p in products if p["id"] != pid]
    save_products(products)
    await q.answer("Удалено")
    q.data = "adm_products"
    await adm_products_list(update, context)

# ━━━ РЕДАКТИРОВАНИЕ ТОВАРА ━━━
async def adm_edit_start(update: Update, context):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("Нет доступа"); return ConversationHandler.END
    pid = int(q.data.split("_")[1])
    context.user_data["edit_pid"] = pid
    await q.answer()
    kb = [
        [InlineKeyboardButton("Название", callback_data="editf_name")],
        [InlineKeyboardButton("Цена", callback_data="editf_price")],
        [InlineKeyboardButton("Описание", callback_data="editf_description")],
        [InlineKeyboardButton("Размеры", callback_data="editf_sizes")],
        [InlineKeyboardButton("Цвета", callback_data="editf_colors")],
        [InlineKeyboardButton("✕ Отмена", callback_data="adm_products")],
    ]
    await q.edit_message_text("Что изменить?", reply_markup=InlineKeyboardMarkup(kb))
    return ADM_EDIT_FIELD

async def adm_edit_field(update: Update, context):
    q = update.callback_query
    await q.answer()
    field = q.data.split("_")[1]
    context.user_data["edit_field"] = field
    labels = {"name": "название", "price": "цену", "description": "описание", "sizes": "размеры", "colors": "цвета"}
    await q.edit_message_text(f"Введите новое {labels.get(field, field)}:")
    return ADM_EDIT_VALUE

async def adm_edit_value(update: Update, context):
    field = context.user_data["edit_field"]
    pid = context.user_data["edit_pid"]
    value = update.message.text
    products = get_products()
    for p in products:
        if p["id"] == pid:
            if field == "price":
                try:
                    value = int(value.replace(" ", "").replace("₽", ""))
                except:
                    await update.message.reply_text("Введите число:"); return ADM_EDIT_VALUE
            p[field] = value
            break
    save_products(products)
    await update.message.reply_text(
        f"✅ Обновлено!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀ АДМИН", callback_data="adm_home")]])
    )
    return ConversationHandler.END

# ━━━ ЗАМЕНА ФОТО ━━━
async def adm_photo_start(update: Update, context):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("Нет доступа"); return ConversationHandler.END
    context.user_data["photo_pid"] = int(q.data.split("_")[1])
    await q.answer()
    await q.edit_message_text("Отправьте новое фото:")
    return ADM_PHOTO

async def adm_photo_receive(update: Update, context):
    if not update.message.photo:
        await update.message.reply_text("Отправьте фото:"); return ADM_PHOTO
    pid = context.user_data["photo_pid"]
    products = get_products()
    for p in products:
        if p["id"] == pid:
            p["photo"] = update.message.photo[-1].file_id
            break
    save_products(products)
    await update.message.reply_text("✅ Фото обновлено!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀ АДМИН", callback_data="adm_home")]]))
    return ConversationHandler.END

# ━━━ КАТЕГОРИИ ━━━
async def adm_categories_menu(update: Update, context):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("Нет доступа"); return
    await q.answer()
    cats = get_categories()
    text = "━━━ КАТЕГОРИИ ━━━\n\n"
    kb = []
    if cats:
        for c in cats:
            text += f"{c.get('emoji','📂')} {c['name']}\n"
            kb.append([InlineKeyboardButton(f"🗑 {c['name']}", callback_data=f"delcat_{c['name']}")])
    else:
        text += "Нет категорий\n"
    kb.append([InlineKeyboardButton("➕ ДОБАВИТЬ", callback_data="adm_addcat")])
    kb.append([InlineKeyboardButton("◀ АДМИН", callback_data="adm_home")])
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

async def adm_addcat_start(update: Update, context):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("Название категории:")
    return ADM_CAT_NAME

async def adm_addcat_name(update: Update, context):
    context.user_data["new_cat"] = update.message.text
    await update.message.reply_text("Эмодзи для категории (или «нет»):")
    return ADM_CAT_EMOJI

async def adm_addcat_emoji(update: Update, context):
    emoji = update.message.text if update.message.text.lower() not in ("нет","-") else "📂"
    cats = get_categories()
    cats.append({"name": context.user_data["new_cat"], "emoji": emoji})
    save_categories(cats)
    await update.message.reply_text("✅ Категория добавлена!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀ АДМИН", callback_data="adm_home")]]))
    return ConversationHandler.END

async def adm_delete_cat(update: Update, context):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("Нет доступа"); return
    name = q.data[7:]
    cats = get_categories()
    cats = [c for c in cats if c["name"] != name]
    save_categories(cats)
    await q.answer("Удалено")
    q.data = "adm_categories"
    await adm_categories_menu(update, context)

# ━━━ ЗАКАЗЫ (АДМИН) ━━━
async def adm_orders_list(update: Update, context):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("Нет доступа"); return
    await q.answer()
    orders = get_orders()
    if not orders:
        await q.edit_message_text("Нет заказов.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀ АДМИН", callback_data="adm_home")]]))
        return
    status_map = {"new": "🆕", "confirmed": "✅", "shipped": "🚚", "delivered": "📦", "cancelled": "❌"}
    kb = []
    for o in orders[-20:]:
        st = status_map.get(o["status"], "❓")
        kb.append([InlineKeyboardButton(
            f"{st} #{o['id']}  {o.get('name','')}  {fmt_price(o['total'])}",
            callback_data=f"admord_{o['id']}"
        )])
    kb.append([InlineKeyboardButton("◀ АДМИН", callback_data="adm_home")])
    await q.edit_message_text("ЗАКАЗЫ:", reply_markup=InlineKeyboardMarkup(kb))

async def adm_order_detail(update: Update, context):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("Нет доступа"); return
    await q.answer()
    oid = int(q.data.split("_")[1])
    orders = get_orders()
    o = next((x for x in orders if x["id"] == oid), None)
    if not o:
        await q.edit_message_text("Не найден."); return
    status_map = {"new": "🆕 Новый", "confirmed": "✅ Подтверждён", "shipped": "🚚 Отправлен",
                  "delivered": "📦 Доставлен", "cancelled": "❌ Отменён"}
    text = (
        f"ЗАКАЗ #{o['id']}\n"
        f"Статус: {status_map.get(o['status'], o['status'])}\n"
        f"Дата: {o.get('created','—')[:16]}\n\n"
        f"Клиент: {o.get('name','—')}\n"
        f"Тел: {o.get('phone','—')}\n"
        f"Адрес: {o.get('address','—')}\n"
        f"Комм.: {o.get('comment','—')}\n"
        f"@{o.get('username','—')}\n\n"
    )
    for it in o.get("items", []):
        text += f"▸ {it['name']} ×{it['qty']} — {fmt_price(it['price']*it['qty'])}\n"
    text += f"\nИТОГО: {fmt_price(o['total'])}"
    kb = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data=f"ordstatus_{oid}_confirmed")],
        [InlineKeyboardButton("🚚 Отправлен", callback_data=f"ordstatus_{oid}_shipped")],
        [InlineKeyboardButton("📦 Доставлен", callback_data=f"ordstatus_{oid}_delivered")],
        [InlineKeyboardButton("❌ Отменить", callback_data=f"ordstatus_{oid}_cancelled")],
        [InlineKeyboardButton("◀ К ЗАКАЗАМ", callback_data="adm_orders")],
    ]
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

async def adm_change_order_status(update: Update, context):
    q = update.callback_query
    parts = q.data.split("_")
    oid = int(parts[1])
    new_status = parts[2]
    orders = get_orders()
    user_id = None
    for o in orders:
        if o["id"] == oid:
            o["status"] = new_status
            user_id = o.get("user_id")
            break
    save_orders(orders)
    await q.answer(f"Статус → {new_status}")

    # Уведомление клиенту
    status_text = {"confirmed": "✅ подтверждён", "shipped": "🚚 отправлен",
                   "delivered": "📦 доставлен", "cancelled": "❌ отменён"}
    if user_id:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"Ваш заказ #{oid} {status_text.get(new_status, new_status)}!"
            )
        except:
            pass

    # Обновляем карточку если админ
    if is_admin(q.from_user.id):
        q.data = f"admord_{oid}"
        await adm_order_detail(update, context)

# ━━━ СТАТИСТИКА ━━━
async def adm_stats(update: Update, context):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("Нет доступа"); return
    await q.answer()
    products = get_products()
    orders = get_orders()
    total_revenue = sum(o["total"] for o in orders if o["status"] not in ("cancelled",))
    new_o = len([o for o in orders if o["status"] == "new"])
    conf_o = len([o for o in orders if o["status"] == "confirmed"])
    ship_o = len([o for o in orders if o["status"] == "shipped"])
    text = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "     СТАТИСТИКА\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Товаров: {len(products)}\n"
        f"Заказов всего: {len(orders)}\n\n"
        f"🆕 Новых: {new_o}\n"
        f"✅ Подтверждённых: {conf_o}\n"
        f"🚚 В доставке: {ship_o}\n\n"
        f"💰 Выручка: {fmt_price(total_revenue)}"
    )
    await q.edit_message_text(text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀ АДМИН", callback_data="adm_home")]]))

# ━━━ РАССЫЛКА ━━━
async def adm_broadcast_start(update: Update, context):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("Нет доступа"); return ConversationHandler.END
    await q.answer()
    await q.edit_message_text("Введите текст рассылки:\n(получат все, кто делал заказы)")
    return ADM_BROADCAST_TEXT

async def adm_broadcast_send(update: Update, context):
    text = update.message.text
    orders = get_orders()
    user_ids = list(set(o["user_id"] for o in orders))
    sent = 0
    for uid in user_ids:
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 {SHOP_NAME}\n\n{text}")
            sent += 1
        except:
            pass
    await update.message.reply_text(f"✅ Отправлено: {sent} из {len(user_ids)}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀ АДМИН", callback_data="adm_home")]]))
    return ConversationHandler.END

async def adm_home_btn(update: Update, context):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("Нет доступа"); return
    await q.answer()
    try:
        await q.message.delete()
    except:
        pass
    await show_admin_menu(q.message, context)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CALLBACK ROUTER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def callback_router(update: Update, context):
    q = update.callback_query
    data = q.data
    if data == "home":
        await start(update, context)
    elif data == "catalog":
        await catalog_menu(update, context)
    elif data.startswith("cat_"):
        await category_products(update, context)
    elif data.startswith("prod_"):
        await product_card(update, context)
    elif data.startswith("addcart_"):
        await add_to_cart(update, context)
    elif data.startswith("buynow_"):
        await buy_now(update, context)
    elif data == "cart":
        await cart_view(update, context)
    elif data.startswith("cartplus_") or data.startswith("cartminus_"):
        await cart_adjust(update, context)
    elif data == "cart_clear":
        await cart_clear(update, context)
    elif data == "my_orders":
        await my_orders(update, context)
    elif data == "contact":
        await contact_view(update, context)
    elif data == "how_to":
        await how_to_view(update, context)
    elif data == "noop":
        await q.answer()
    # Админ
    elif data == "adm_home":
        await adm_home_btn(update, context)
    elif data == "adm_products":
        await adm_products_list(update, context)
    elif data.startswith("admprod_"):
        await adm_product_detail(update, context)
    elif data.startswith("admtoggle_"):
        await adm_toggle_visible(update, context)
    elif data.startswith("admdel_"):
        await adm_delete_product(update, context)
    elif data == "adm_categories":
        await adm_categories_menu(update, context)
    elif data.startswith("delcat_"):
        await adm_delete_cat(update, context)
    elif data == "adm_orders":
        await adm_orders_list(update, context)
    elif data.startswith("admord_"):
        await adm_order_detail(update, context)
    elif data.startswith("ordstatus_"):
        await adm_change_order_status(update, context)
    elif data == "adm_stats":
        await adm_stats(update, context)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def main():
    ensure_data_dir()
    app = Application.builder().token(BOT_TOKEN).build()

    # Checkout conversation
    checkout_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(checkout_start, pattern="^checkout$")],
        states={
            CHECKOUT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, checkout_name)],
            CHECKOUT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, checkout_phone)],
            CHECKOUT_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, checkout_address)],
            CHECKOUT_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, checkout_finish)],
        },
        fallbacks=[CallbackQueryHandler(checkout_cancel, pattern="^cart$")],
        per_message=False,
    )

    # Add product conversation
    addprod_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm_addprod_start, pattern="^adm_addprod$")],
        states={
            ADM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_addprod_name)],
            ADM_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_addprod_price)],
            ADM_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_addprod_desc)],
            ADM_SIZES: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_addprod_sizes)],
            ADM_COLORS: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_addprod_colors)],
            ADM_CATEGORY: [
                CallbackQueryHandler(adm_addprod_category, pattern="^setcat_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, adm_addprod_category),
            ],
            ADM_PHOTO: [
                MessageHandler(filters.PHOTO, adm_addprod_photo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, adm_addprod_photo),
            ],
        },
        fallbacks=[CallbackQueryHandler(checkout_cancel, pattern="^adm_home$")],
        per_message=False,
    )

    # Edit product conversation
    edit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm_edit_start, pattern=r"^admedit_\d+$")],
        states={
            ADM_EDIT_FIELD: [CallbackQueryHandler(adm_edit_field, pattern="^editf_")],
            ADM_EDIT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_edit_value)],
        },
        fallbacks=[CallbackQueryHandler(checkout_cancel, pattern="^adm_products$")],
        per_message=False,
    )

    # Photo replace conversation
    photo_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm_photo_start, pattern=r"^admphoto_\d+$")],
        states={
            ADM_PHOTO: [
                MessageHandler(filters.PHOTO, adm_photo_receive),
                MessageHandler(filters.TEXT & ~filters.COMMAND, adm_photo_receive),
            ],
        },
        fallbacks=[CallbackQueryHandler(checkout_cancel, pattern="^adm_home$")],
        per_message=False,
    )

    # Add category conversation
    addcat_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm_addcat_start, pattern="^adm_addcat$")],
        states={
            ADM_CAT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_addcat_name)],
            ADM_CAT_EMOJI: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_addcat_emoji)],
        },
        fallbacks=[CallbackQueryHandler(checkout_cancel, pattern="^adm_home$")],
        per_message=False,
    )

    # Broadcast conversation
    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm_broadcast_start, pattern="^adm_broadcast$")],
        states={
            ADM_BROADCAST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_broadcast_send)],
        },
        fallbacks=[CallbackQueryHandler(checkout_cancel, pattern="^adm_home$")],
        per_message=False,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(checkout_conv)
    app.add_handler(addprod_conv)
    app.add_handler(edit_conv)
    app.add_handler(photo_conv)
    app.add_handler(addcat_conv)
    app.add_handler(broadcast_conv)
    app.add_handler(CallbackQueryHandler(callback_router))

    logger.info(f"🚀 {SHOP_NAME} бот запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
