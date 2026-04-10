import os, json, logging, datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters
)

# ═══════════════════════════════════════════
#  НАСТРОЙКИ
# ═══════════════════════════════════════════
TOKEN = "8674017448:AAF0DE0OQMVFzGCGSKYV1P30Rfezd-LGTN0"
SHOP = "HAMASHA PARFUM"
MANAGER = "@sulik"
DATA = "data"

DELIVERY_TEXT = (
    "🚚  ДОСТАВКА\n\n"
    "▸ По городу — бесплатно\n"
    "▸ По России — от 300 ₽ (СДЭК / Почта)\n"
    "▸ Срок — 1-5 дней\n\n"
    "💳  ОПЛАТА\n\n"
    "▸ Наличные при получении\n"
    "▸ Перевод на карту\n"
)

logging.basicConfig(level=logging.INFO)

# ═══════════════════════════════════════════
#  ХРАНИЛИЩЕ (JSON)
# ═══════════════════════════════════════════
def _path(name): return os.path.join(DATA, name)
def _load(name, default=None):
    try:
        with open(_path(name), "r", encoding="utf-8") as f: return json.load(f)
    except: return default if default is not None else []
def _save(name, data):
    os.makedirs(DATA, exist_ok=True)
    with open(_path(name), "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

def products():    return _load("products.json", [])
def categories():  return _load("categories.json", [])
def orders():      return _load("orders.json", [])
def admins():      return _load("admins.json", [])
def carts():       return _load("carts.json", {})
def promos():      return _load("promos.json", [])

def save_products(d):   _save("products.json", d)
def save_categories(d): _save("categories.json", d)
def save_orders(d):     _save("orders.json", d)
def save_admins(d):     _save("admins.json", d)
def save_carts(d):      _save("carts.json", d)
def save_promos(d):     _save("promos.json", d)

def is_admin(uid): return uid in admins()
def price(v): return f'{v:,.0f}'.replace(',', ' ') + ' ₽'
def next_id(lst): return max([x.get("id",0) for x in lst], default=0) + 1

def get_cart(uid):
    c = carts(); return c.get(str(uid), [])
def set_cart(uid, cart):
    c = carts(); c[str(uid)] = cart; save_carts(c)
def clear_cart(uid):
    c = carts(); c.pop(str(uid), None); save_carts(c)

def cart_total(uid):
    cart = get_cart(uid); pp = products(); total = 0
    for i in cart:
        p = next((x for x in pp if x["id"]==i["pid"]), None)
        if p: total += p["price"] * i["qty"]
    return total

# ═══════════════════════════════════════════
#  КНОПКИ-ХЕЛПЕРЫ
# ═══════════════════════════════════════════
def btn(text, data): return InlineKeyboardButton(text, callback_data=data)
def url_btn(text, url): return InlineKeyboardButton(text, url=url)
def back(data="home", label="◀ Назад"): return [btn(label, data)]

# safe edit — если нельзя edit, отправим новое
async def reply(q, text, kb=None, **kw):
    markup = InlineKeyboardMarkup(kb) if kb else None
    try:
        await q.edit_message_text(text, reply_markup=markup, **kw)
    except:
        await q.message.reply_text(text, reply_markup=markup, **kw)

# ═══════════════════════════════════════════
#  /start — ГЛАВНАЯ
# ═══════════════════════════════════════════
WELCOME = (
    f"✦  {SHOP}  ✦\n"
    f"━━━━━━━━━━━━━━━━━━━━\n\n"
    f"Парфюмерия на любой вкус.\n"
    f"Оригиналы и селектив."
)

HOME_KB = [
    [btn("🛍  Каталог", "catalog")],
    [btn("🛒  Корзина", "cart"), btn("📦  Мои заказы", "my_orders")],
    [btn("🔥  Акции", "promos")],
    [btn("🚚  Доставка и оплата", "delivery")],
    [btn("💬  Написать нам", "contact")],
]

async def cmd_start(update: Update, ctx):
    msg = update.callback_query or update
    if hasattr(msg, 'answer'): await msg.answer()
    if hasattr(msg, 'edit_message_text'):
        await reply(msg, WELCOME, HOME_KB)
    else:
        await update.message.reply_text(WELCOME, reply_markup=InlineKeyboardMarkup(HOME_KB))

# ═══════════════════════════════════════════
#  КАТАЛОГ
# ═══════════════════════════════════════════
async def catalog(q, ctx):
    await q.answer()
    cats = categories(); pp = [p for p in products() if p.get("visible", True)]
    if not pp:
        return await reply(q, "Каталог обновляется, загляните позже 🌸", [back()])
    kb = []
    if cats:
        for c in cats:
            n = len([p for p in pp if p.get("cat") == c["name"]])
            if n: kb.append([btn(f'{c.get("emoji","🔹")}  {c["name"]}  ({n})', f'cat:{c["name"]}')])
        uncategorized = [p for p in pp if not p.get("cat")]
        if uncategorized:
            kb.append([btn(f'🔹  Другое  ({len(uncategorized)})', 'cat:')])
    else:
        for p in pp:
            label = f'{p["name"]}  ·  {price(p["price"])}'
            kb.append([btn(label, f'p:{p["id"]}')])
    kb.append(back())
    await reply(q, f"✦  КАТАЛОГ  ✦\n━━━━━━━━━━━━━━━━━━━━", kb)

async def cat_list(q, ctx):
    await q.answer()
    name = q.data.split(":", 1)[1]
    pp = [p for p in products() if p.get("visible", True)]
    items = [p for p in pp if (p.get("cat") or "") == name] if name != "" else [p for p in pp if not p.get("cat")]
    title = name or "Другое"
    kb = []
    for p in items:
        lab = f'{p["name"]}  ·  {price(p["price"])}'
        kb.append([btn(lab, f'p:{p["id"]}')])
    kb.append(back("catalog", "◀ Каталог"))
    await reply(q, f"✦  {title.upper()}  ✦\n━━━━━━━━━━━━━━━━━━━━", kb)

async def product_card(q, ctx):
    await q.answer()
    pid = int(q.data.split(":")[1])
    p = next((x for x in products() if x["id"] == pid), None)
    if not p: return await reply(q, "Товар не найден", [back("catalog")])

    lines = [f"✦  {p['name'].upper()}  ✦", "━━━━━━━━━━━━━━━━━━━━", ""]
    if p.get("desc"):    lines.append(p["desc"])
    if p.get("volume"):  lines.append(f"📏  {p['volume']}")
    if p.get("notes"):   lines.append(f"🌿  Ноты: {p['notes']}")
    if p.get("gender"):  lines.append(f"👤  {p['gender']}")
    lines.append("")
    if p.get("old_price"):
        lines.append(f"💰  {price(p['price'])}  (было {price(p['old_price'])})")
    else:
        lines.append(f"💰  {price(p['price'])}")
    text = "\n".join(lines)

    kb = [
        [btn("🛒  В корзину", f"add:{pid}"), btn("⚡ Купить", f"buy:{pid}")],
        [btn("◀ Каталог", "catalog")],
    ]
    # Удаляем старое и шлём с фото если есть
    try: await q.message.delete()
    except: pass
    if p.get("photo"):
        await ctx.bot.send_photo(q.message.chat_id, p["photo"], caption=text,
                                 reply_markup=InlineKeyboardMarkup(kb))
    else:
        await ctx.bot.send_message(q.message.chat_id, text, reply_markup=InlineKeyboardMarkup(kb))

# ═══════════════════════════════════════════
#  КОРЗИНА
# ═══════════════════════════════════════════
async def add_to_cart(q, ctx):
    pid = int(q.data.split(":")[1]); uid = q.from_user.id
    cart = get_cart(uid)
    item = next((i for i in cart if i["pid"] == pid), None)
    if item: item["qty"] += 1
    else: cart.append({"pid": pid, "qty": 1})
    set_cart(uid, cart)
    await q.answer("✓ Добавлено в корзину")

async def cart_view(q, ctx):
    await q.answer()
    uid = q.from_user.id; cart = get_cart(uid); pp = products()
    if not cart:
        return await reply(q, "Корзина пуста 🛒", [[btn("🛍  В каталог", "catalog")], back()])

    lines = ["✦  КОРЗИНА  ✦", "━━━━━━━━━━━━━━━━━━━━", ""]
    total = 0; kb = []
    for i in cart:
        p = next((x for x in pp if x["id"] == i["pid"]), None)
        if not p: continue
        s = p["price"] * i["qty"]; total += s
        lines.append(f'▸ {p["name"]}  ×{i["qty"]}  —  {price(s)}')
        kb.append([btn("➖", f"c-:{i['pid']}"), btn(f'{i["qty"]} шт', "noop"), btn("➕", f"c+:{i['pid']}")])
    lines += ["", "━━━━━━━━━━━━━━━━━━━━", f"Итого: {price(total)}"]
    kb.append([btn("📦  Оформить заказ", "checkout")])
    kb.append([btn("🗑  Очистить", "cart_clear")])
    kb.append(back())
    await reply(q, "\n".join(lines), kb)

async def cart_adj(q, ctx):
    parts = q.data.split(":"); op = parts[0]; pid = int(parts[1])
    uid = q.from_user.id; cart = get_cart(uid)
    for i in cart:
        if i["pid"] == pid:
            i["qty"] += 1 if op == "c+" else -1
            if i["qty"] <= 0: cart.remove(i)
            break
    set_cart(uid, cart)
    q.data = "cart"
    await cart_view(q, ctx)

async def cart_clear_fn(q, ctx):
    clear_cart(q.from_user.id); await q.answer("Очищено")
    q.data = "cart"; await cart_view(q, ctx)

# ═══════════════════════════════════════════
#  ОФОРМЛЕНИЕ ЗАКАЗА
# ═══════════════════════════════════════════
S_NAME, S_PHONE, S_ADDR = range(3)

async def checkout_start(q, ctx):
    await q.answer()
    if not get_cart(q.from_user.id):
        return await reply(q, "Корзина пуста.", [back()])
    await reply(q, "📦  ОФОРМЛЕНИЕ ЗАКАЗА\n━━━━━━━━━━━━━━━━━━━━\n\nВаше имя:")
    ctx.user_data["order"] = {"uid": q.from_user.id, "uname": q.from_user.username}
    return S_NAME

async def o_name(update, ctx):
    ctx.user_data["order"]["name"] = update.message.text
    await update.message.reply_text("📱  Номер телефона:")
    return S_PHONE

async def o_phone(update, ctx):
    ctx.user_data["order"]["phone"] = update.message.text
    await update.message.reply_text("📍  Адрес доставки (или «самовывоз»):")
    return S_ADDR

async def o_done(update, ctx):
    info = ctx.user_data["order"]
    info["address"] = update.message.text
    uid = info["uid"]; cart = get_cart(uid); pp = products()
    oid = next_id(orders()); items = []; total = 0
    for ci in cart:
        p = next((x for x in pp if x["id"] == ci["pid"]), None)
        if not p: continue
        items.append({"name": p["name"], "price": p["price"], "qty": ci["qty"]})
        total += p["price"] * ci["qty"]

    order = {
        "id": oid, "uid": uid, "uname": info.get("uname",""),
        "name": info["name"], "phone": info["phone"], "address": info["address"],
        "items": items, "total": total, "status": "new",
        "date": datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    oo = orders(); oo.append(order); save_orders(oo); clear_cart(uid)

    # Клиенту
    lines = [f"✅  Заказ #{oid} принят!", "━━━━━━━━━━━━━━━━━━━━", ""]
    for i in items: lines.append(f"▸ {i['name']}  ×{i['qty']}  —  {price(i['price']*i['qty'])}")
    lines += ["", f"Итого: {price(total)}", "", f"📱  {info['name']}  ·  {info['phone']}",
              f"📍  {info['address']}", "", "Мы свяжемся с вами для подтверждения!"]
    await update.message.reply_text("\n".join(lines),
        reply_markup=InlineKeyboardMarkup([back()]))

    # Админам
    atxt = (f"🔔  ЗАКАЗ #{oid}\n\n{info['name']}\n{info['phone']}\n{info['address']}\n"
            f"@{info.get('uname','—')}\n\n")
    for i in items: atxt += f"▸ {i['name']} ×{i['qty']} — {price(i['price']*i['qty'])}\n"
    atxt += f"\nИтого: {price(total)}"
    akb = InlineKeyboardMarkup([
        [btn("✅ Принять", f"os:{oid}:confirmed"), btn("❌ Отклонить", f"os:{oid}:cancelled")],
        [btn("🚚 Отправлен", f"os:{oid}:shipped"), btn("📦 Доставлен", f"os:{oid}:delivered")],
    ])
    for a in admins():
        try: await ctx.bot.send_message(a, atxt, reply_markup=akb)
        except: pass
    return ConversationHandler.END

async def o_cancel(update, ctx):
    if update.callback_query: await update.callback_query.answer()
    return ConversationHandler.END

# ═══════════════════════════════════════════
#  БЫСТРАЯ ПОКУПКА
# ═══════════════════════════════════════════
async def buy_now(q, ctx):
    pid = int(q.data.split(":")[1])
    set_cart(q.from_user.id, [{"pid": pid, "qty": 1}])
    return await checkout_start(q, ctx)

# ═══════════════════════════════════════════
#  МОИ ЗАКАЗЫ / ДОСТАВКА / КОНТАКТ / АКЦИИ
# ═══════════════════════════════════════════
async def my_orders(q, ctx):
    await q.answer()
    oo = [o for o in orders() if o["uid"] == q.from_user.id]
    if not oo: return await reply(q, "У вас пока нет заказов.", [back()])
    st = {"new":"🆕 Новый","confirmed":"✅ Принят","shipped":"🚚 Отправлен","delivered":"📦 Доставлен","cancelled":"❌ Отменён"}
    lines = ["✦  МОИ ЗАКАЗЫ  ✦", "━━━━━━━━━━━━━━━━━━━━", ""]
    for o in oo[-10:]:
        lines.append(f'#{o["id"]}  ·  {price(o["total"])}  ·  {st.get(o["status"],o["status"])}')
        lines.append(f'     {o.get("date","")}')
        lines.append("")
    await reply(q, "\n".join(lines), [back()])

async def delivery(q, ctx):
    await q.answer(); await reply(q, DELIVERY_TEXT, [back()])

async def contact(q, ctx):
    await q.answer()
    await reply(q, f"💬  Напишите нам — ответим быстро!\n\nМенеджер: {MANAGER}",
        [[url_btn("✉️  Написать", f"https://t.me/{MANAGER.lstrip('@')}")], back()])

async def promos_view(q, ctx):
    await q.answer()
    pp = promos()
    if not pp:
        return await reply(q, "Сейчас акций нет.\nСледите за обновлениями! 🌸", [back()])
    lines = ["🔥  АКЦИИ  🔥", "━━━━━━━━━━━━━━━━━━━━", ""]
    for p in pp:
        lines.append(f'✦  {p["title"]}')
        if p.get("desc"): lines.append(f'    {p["desc"]}')
        lines.append("")
    await reply(q, "\n".join(lines), [back()])

# ═══════════════════════════════════════════
#  СМЕНА СТАТУСА ЗАКАЗА
# ═══════════════════════════════════════════
async def order_status_change(q, ctx):
    _, oid, status = q.data.split(":")
    oid = int(oid)
    oo = orders()
    o = next((x for x in oo if x["id"] == oid), None)
    if not o: await q.answer("Не найден"); return
    o["status"] = status; save_orders(oo)
    st_text = {"confirmed":"✅ принят","shipped":"🚚 отправлен","delivered":"📦 доставлен","cancelled":"❌ отменён"}
    await q.answer(f"Статус → {status}")
    try: await ctx.bot.send_message(o["uid"], f"Заказ #{oid} — {st_text.get(status, status)}!")
    except: pass

# ═══════════════════════════════════════════
#  АДМИН-ПАНЕЛЬ  /admin
# ═══════════════════════════════════════════
async def cmd_admin(update, ctx):
    uid = update.effective_user.id
    aa = admins()
    if not aa: aa.append(uid); save_admins(aa)
    if uid not in aa: return await update.message.reply_text("⛔ Нет доступа")
    pp = products(); oo = orders()
    new_o = len([o for o in oo if o["status"] == "new"])
    text = (f"⚙️  АДМИН-ПАНЕЛЬ\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Товаров: {len(pp)}  ·  Заказов: {len(oo)}  (новых: {new_o})")
    kb = [
        [btn("➕ Добавить товар", "a:add")],
        [btn("📋 Товары", "a:prods"), btn("📂 Категории", "a:cats")],
        [btn("📦 Заказы", "a:ords"), btn("📊 Статистика", "a:stats")],
        [btn("🔥 Акции", "a:promos")],
        [btn("📢 Рассылка", "a:bcast")],
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))

async def adm_home(q, ctx):
    if not is_admin(q.from_user.id): await q.answer("⛔"); return
    await q.answer()
    pp = products(); oo = orders(); new_o = len([o for o in oo if o["status"]=="new"])
    text = (f"⚙️  АДМИН-ПАНЕЛЬ\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Товаров: {len(pp)}  ·  Заказов: {len(oo)}  (новых: {new_o})")
    kb = [
        [btn("➕ Добавить товар", "a:add")],
        [btn("📋 Товары", "a:prods"), btn("📂 Категории", "a:cats")],
        [btn("📦 Заказы", "a:ords"), btn("📊 Статистика", "a:stats")],
        [btn("🔥 Акции", "a:promos")],
        [btn("📢 Рассылка", "a:bcast")],
    ]
    try: await q.message.delete()
    except: pass
    await q.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))

# ── Добавление товара ──
A_NAME, A_PRICE, A_DESC, A_VOL, A_NOTES, A_GENDER, A_CAT, A_PHOTO = range(8)

async def a_add_start(q, ctx):
    if not is_admin(q.from_user.id): await q.answer("⛔"); return ConversationHandler.END
    await q.answer()
    await reply(q, "➕  НОВЫЙ ТОВАР\n━━━━━━━━━━━━━━━━━━━━\n\nНазвание:")
    ctx.user_data["np"] = {}
    return A_NAME

async def a_name(u, ctx):
    ctx.user_data["np"]["name"] = u.message.text
    await u.message.reply_text("Цена (число):")
    return A_PRICE

async def a_price(u, ctx):
    try: p = int(u.message.text.replace(" ","").replace("₽",""))
    except: await u.message.reply_text("Введите число:"); return A_PRICE
    ctx.user_data["np"]["price"] = p
    await u.message.reply_text("Описание (или «—»):")
    return A_DESC

async def a_desc(u, ctx):
    t = u.message.text
    if t not in ("—","-","нет"): ctx.user_data["np"]["desc"] = t
    await u.message.reply_text("Объём (напр. 50ml, 100ml) или «—»:")
    return A_VOL

async def a_vol(u, ctx):
    t = u.message.text
    if t not in ("—","-","нет"): ctx.user_data["np"]["volume"] = t
    await u.message.reply_text("Ноты аромата (напр. ваниль, сандал) или «—»:")
    return A_NOTES

async def a_notes(u, ctx):
    t = u.message.text
    if t not in ("—","-","нет"): ctx.user_data["np"]["notes"] = t
    kb = InlineKeyboardMarkup([
        [btn("Мужской", "g:Мужской"), btn("Женский", "g:Женский")],
        [btn("Унисекс", "g:Унисекс"), btn("Пропустить", "g:—")],
    ])
    await u.message.reply_text("Для кого:", reply_markup=kb)
    return A_GENDER

async def a_gender(u, ctx):
    if u.callback_query:
        q = u.callback_query; await q.answer()
        val = q.data.split(":")[1]
        if val != "—": ctx.user_data["np"]["gender"] = val
        cats = categories()
        if cats:
            kb = [[btn(c["name"], f"sc:{c['name']}")] for c in cats]
            kb.append([btn("Без категории", "sc:—")])
            await q.edit_message_text("Категория:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            await q.edit_message_text("Отправьте фото или напишите «—»:")
        return A_CAT
    return A_GENDER

async def a_cat(u, ctx):
    if u.callback_query:
        q = u.callback_query; await q.answer()
        val = q.data.split(":",1)[1]
        if val != "—": ctx.user_data["np"]["cat"] = val
        await q.edit_message_text("Отправьте фото или напишите «—»:")
    else:
        t = u.message.text
        if t not in ("—","-","нет"): ctx.user_data["np"]["cat"] = t
        await u.message.reply_text("Отправьте фото или напишите «—»:")
    return A_PHOTO

async def a_photo(u, ctx):
    np = ctx.user_data["np"]
    if u.message.photo:
        np["photo"] = u.message.photo[-1].file_id
    np["id"] = next_id(products()); np["visible"] = True
    pp = products(); pp.append(np); save_products(pp)
    await u.message.reply_text(
        f"✅  «{np['name']}» добавлен!  ID {np['id']}  ·  {price(np['price'])}",
        reply_markup=InlineKeyboardMarkup([[btn("◀ Админ", "a:home")]]))
    return ConversationHandler.END

# ── Список товаров ──
async def a_prods(q, ctx):
    if not is_admin(q.from_user.id): return
    await q.answer(); pp = products()
    if not pp: return await reply(q, "Нет товаров.", [[btn("◀ Админ", "a:home")]])
    kb = []
    for p in pp:
        vis = "✅" if p.get("visible",True) else "🚫"
        kb.append([btn(f'{vis} {p["name"]} · {price(p["price"])}', f'ap:{p["id"]}')])
    kb.append([btn("◀ Админ", "a:home")])
    await reply(q, "📋  ТОВАРЫ", kb)

async def a_prod_detail(q, ctx):
    if not is_admin(q.from_user.id): return
    await q.answer()
    pid = int(q.data.split(":")[1])
    p = next((x for x in products() if x["id"]==pid), None)
    if not p: return
    vis = "Виден" if p.get("visible",True) else "Скрыт"
    text = (f'ID: {p["id"]}\n{p["name"]}\n{price(p["price"])}\n'
            f'Описание: {p.get("desc","—")}\nОбъём: {p.get("volume","—")}\n'
            f'Ноты: {p.get("notes","—")}\nПол: {p.get("gender","—")}\n'
            f'Категория: {p.get("cat","—")}\nФото: {"да" if p.get("photo") else "нет"}\n{vis}')
    tog = "🚫 Скрыть" if p.get("visible",True) else "👁 Показать"
    kb = [
        [btn("✏️ Изменить", f"ae:{pid}"), btn("📸 Фото", f"aph:{pid}")],
        [btn(tog, f"at:{pid}"), btn("🗑 Удалить", f"ad:{pid}")],
        [btn("◀ Товары", "a:prods")],
    ]
    await reply(q, text, kb)

async def a_toggle(q, ctx):
    if not is_admin(q.from_user.id): return
    pid = int(q.data.split(":")[1]); pp = products()
    for p in pp:
        if p["id"]==pid: p["visible"] = not p.get("visible",True); break
    save_products(pp); await q.answer("Обновлено")
    q.data = f"ap:{pid}"; await a_prod_detail(q, ctx)

async def a_del(q, ctx):
    if not is_admin(q.from_user.id): return
    pid = int(q.data.split(":")[1]); pp = [p for p in products() if p["id"]!=pid]
    save_products(pp); await q.answer("Удалён")
    q.data = "a:prods"; await a_prods(q, ctx)

# ── Редактирование ──
E_FIELD, E_VAL = range(2)
async def ae_start(q, ctx):
    if not is_admin(q.from_user.id): return ConversationHandler.END
    pid = int(q.data.split(":")[1]); ctx.user_data["epid"] = pid; await q.answer()
    kb = [[btn("Название","ef:name"),btn("Цена","ef:price")],
          [btn("Описание","ef:desc"),btn("Объём","ef:volume")],
          [btn("Ноты","ef:notes"),btn("Пол","ef:gender")],
          [btn("Старая цена","ef:old_price")],
          [btn("✕ Отмена","a:prods")]]
    await reply(q, "Что изменить?", kb)
    return E_FIELD

async def ae_field(q, ctx):
    await q.answer(); f = q.data.split(":")[1]; ctx.user_data["efield"] = f
    await reply(q, f"Новое значение для «{f}»:")
    return E_VAL

async def ae_val(u, ctx):
    f = ctx.user_data["efield"]; pid = ctx.user_data["epid"]; v = u.message.text
    pp = products()
    for p in pp:
        if p["id"]==pid:
            if f in ("price","old_price"):
                try: v = int(v.replace(" ","").replace("₽",""))
                except: await u.message.reply_text("Число:"); return E_VAL
            p[f] = v; break
    save_products(pp)
    await u.message.reply_text("✅ Обновлено", reply_markup=InlineKeyboardMarkup([[btn("◀ Админ","a:home")]]))
    return ConversationHandler.END

# ── Замена фото ──
PH = 0
async def aph_start(q, ctx):
    if not is_admin(q.from_user.id): return ConversationHandler.END
    ctx.user_data["phpid"] = int(q.data.split(":")[1]); await q.answer()
    await reply(q, "Отправьте новое фото:")
    return PH

async def aph_recv(u, ctx):
    if not u.message.photo: await u.message.reply_text("Фото:"); return PH
    pid = ctx.user_data["phpid"]; pp = products()
    for p in pp:
        if p["id"]==pid: p["photo"] = u.message.photo[-1].file_id; break
    save_products(pp)
    await u.message.reply_text("✅ Фото обновлено", reply_markup=InlineKeyboardMarkup([[btn("◀ Админ","a:home")]]))
    return ConversationHandler.END

# ── Категории ──
CN, CE = range(2)
async def a_cats(q, ctx):
    if not is_admin(q.from_user.id): return
    await q.answer(); cc = categories()
    text = "📂  КАТЕГОРИИ\n━━━━━━━━━━━━━━━━━━━━\n\n"
    kb = []
    for c in cc:
        text += f'{c.get("emoji","🔹")} {c["name"]}\n'
        kb.append([btn(f'🗑 {c["name"]}', f'dc:{c["name"]}')])
    if not cc: text += "Пусто\n"
    kb.append([btn("➕ Добавить", "a:addcat")])
    kb.append([btn("◀ Админ", "a:home")])
    await reply(q, text, kb)

async def ac_start(q, ctx):
    await q.answer(); await reply(q, "Название категории:")
    return CN

async def ac_name(u, ctx):
    ctx.user_data["cn"] = u.message.text
    await u.message.reply_text("Эмодзи (или «—»):")
    return CE

async def ac_emoji(u, ctx):
    e = u.message.text if u.message.text not in ("—","-") else "🔹"
    cc = categories(); cc.append({"name": ctx.user_data["cn"], "emoji": e}); save_categories(cc)
    await u.message.reply_text("✅ Добавлена", reply_markup=InlineKeyboardMarkup([[btn("◀ Админ","a:home")]]))
    return ConversationHandler.END

async def dc(q, ctx):
    if not is_admin(q.from_user.id): return
    name = q.data.split(":",1)[1]; cc = [c for c in categories() if c["name"]!=name]
    save_categories(cc); await q.answer("Удалена")
    q.data = "a:cats"; await a_cats(q, ctx)

# ── Заказы ──
async def a_ords(q, ctx):
    if not is_admin(q.from_user.id): return
    await q.answer(); oo = orders()
    if not oo: return await reply(q, "Нет заказов.", [[btn("◀ Админ","a:home")]])
    st = {"new":"🆕","confirmed":"✅","shipped":"🚚","delivered":"📦","cancelled":"❌"}
    kb = []
    for o in oo[-20:]:
        kb.append([btn(f'{st.get(o["status"],"❓")} #{o["id"]} {o.get("name","")} · {price(o["total"])}', f'ao:{o["id"]}')])
    kb.append([btn("◀ Админ", "a:home")])
    await reply(q, "📦  ЗАКАЗЫ", kb)

async def a_ord_detail(q, ctx):
    if not is_admin(q.from_user.id): return
    await q.answer(); oid = int(q.data.split(":")[1])
    o = next((x for x in orders() if x["id"]==oid), None)
    if not o: return
    st = {"new":"🆕 Новый","confirmed":"✅ Принят","shipped":"🚚 Отправлен","delivered":"📦 Доставлен","cancelled":"❌ Отменён"}
    text = (f'Заказ #{o["id"]}  ·  {st.get(o["status"],o["status"])}\n{o.get("date","")}\n\n'
            f'{o.get("name","")}\n{o.get("phone","")}\n{o.get("address","")}\n@{o.get("uname","—")}\n\n')
    for i in o.get("items",[]): text += f'▸ {i["name"]} ×{i["qty"]} — {price(i["price"]*i["qty"])}\n'
    text += f'\nИтого: {price(o["total"])}'
    kb = [
        [btn("✅ Принять", f"os:{oid}:confirmed"), btn("❌ Отклонить", f"os:{oid}:cancelled")],
        [btn("🚚 Отправлен", f"os:{oid}:shipped"), btn("📦 Доставлен", f"os:{oid}:delivered")],
        [btn("◀ Заказы", "a:ords")],
    ]
    await reply(q, text, kb)

# ── Статистика ──
async def a_stats(q, ctx):
    if not is_admin(q.from_user.id): return
    await q.answer(); oo = orders()
    rev = sum(o["total"] for o in oo if o["status"] not in ("cancelled",))
    text = (f"📊  СТАТИСТИКА\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Товаров: {len(products())}\nЗаказов: {len(oo)}\n\n"
            f"🆕 Новых: {len([o for o in oo if o['status']=='new'])}\n"
            f"✅ Принятых: {len([o for o in oo if o['status']=='confirmed'])}\n"
            f"🚚 В пути: {len([o for o in oo if o['status']=='shipped'])}\n\n"
            f"💰 Выручка: {price(rev)}")
    await reply(q, text, [[btn("◀ Админ","a:home")]])

# ── Акции (админ) ──
PA_TITLE, PA_DESC = range(2)
async def a_promos(q, ctx):
    if not is_admin(q.from_user.id): return
    await q.answer(); pp = promos()
    text = "🔥  АКЦИИ (управление)\n━━━━━━━━━━━━━━━━━━━━\n\n"
    kb = []
    for i, p in enumerate(pp):
        text += f'{i+1}. {p["title"]}\n'
        kb.append([btn(f'🗑 {p["title"]}', f"dp:{i}")])
    if not pp: text += "Нет акций\n"
    kb.append([btn("➕ Добавить акцию", "a:addpromo")])
    kb.append([btn("◀ Админ", "a:home")])
    await reply(q, text, kb)

async def ap_start(q, ctx):
    await q.answer(); await reply(q, "Название акции:")
    return PA_TITLE

async def ap_title(u, ctx):
    ctx.user_data["pt"] = u.message.text
    await u.message.reply_text("Описание (или «—»):")
    return PA_DESC

async def ap_desc(u, ctx):
    d = u.message.text if u.message.text not in ("—","-") else ""
    pp = promos(); pp.append({"title": ctx.user_data["pt"], "desc": d}); save_promos(pp)
    await u.message.reply_text("✅ Акция добавлена", reply_markup=InlineKeyboardMarkup([[btn("◀ Админ","a:home")]]))
    return ConversationHandler.END

async def dp(q, ctx):
    if not is_admin(q.from_user.id): return
    idx = int(q.data.split(":")[1]); pp = promos()
    if 0 <= idx < len(pp): pp.pop(idx); save_promos(pp)
    await q.answer("Удалена"); q.data = "a:promos"; await a_promos(q, ctx)

# ── Рассылка ──
BC = 0
async def bc_start(q, ctx):
    if not is_admin(q.from_user.id): return ConversationHandler.END
    await q.answer(); await reply(q, "Текст рассылки:")
    return BC

async def bc_send(u, ctx):
    text = u.message.text; oo = orders()
    uids = list(set(o["uid"] for o in oo)); sent = 0
    for uid in uids:
        try: await ctx.bot.send_message(uid, f"✦ {SHOP} ✦\n\n{text}"); sent += 1
        except: pass
    await u.message.reply_text(f"✅ Отправлено: {sent}/{len(uids)}",
        reply_markup=InlineKeyboardMarkup([[btn("◀ Админ","a:home")]]))
    return ConversationHandler.END

# ═══════════════════════════════════════════
#  РОУТЕР
# ═══════════════════════════════════════════
async def router(update: Update, ctx):
    q = update.callback_query; d = q.data
    if d == "home": await cmd_start(update, ctx)
    elif d == "catalog": await catalog(q, ctx)
    elif d.startswith("cat:"): await cat_list(q, ctx)
    elif d.startswith("p:"): await product_card(q, ctx)
    elif d.startswith("add:"): await add_to_cart(q, ctx)
    elif d == "cart": await cart_view(q, ctx)
    elif d.startswith("c+:") or d.startswith("c-:"): await cart_adj(q, ctx)
    elif d == "cart_clear": await cart_clear_fn(q, ctx)
    elif d == "my_orders": await my_orders(q, ctx)
    elif d == "delivery": await delivery(q, ctx)
    elif d == "contact": await contact(q, ctx)
    elif d == "promos": await promos_view(q, ctx)
    elif d == "noop": await q.answer()
    # admin
    elif d == "a:home": await adm_home(q, ctx)
    elif d == "a:prods": await a_prods(q, ctx)
    elif d.startswith("ap:") and not d.startswith("ap:0"): await a_prod_detail(q, ctx)
    elif d.startswith("ap:"): await a_prod_detail(q, ctx)
    elif d.startswith("at:"): await a_toggle(q, ctx)
    elif d.startswith("ad:"): await a_del(q, ctx)
    elif d == "a:cats": await a_cats(q, ctx)
    elif d.startswith("dc:"): await dc(q, ctx)
    elif d == "a:ords": await a_ords(q, ctx)
    elif d.startswith("ao:"): await a_ord_detail(q, ctx)
    elif d.startswith("os:"): await order_status_change(q, ctx)
    elif d == "a:stats": await a_stats(q, ctx)
    elif d == "a:promos": await a_promos(q, ctx)
    elif d.startswith("dp:"): await dp(q, ctx)

# ═══════════════════════════════════════════
#  ЗАПУСК
# ═══════════════════════════════════════════
def main():
    os.makedirs(DATA, exist_ok=True)
    app = Application.builder().token(TOKEN).build()

    # Conversations
    checkout = ConversationHandler(
        entry_points=[CallbackQueryHandler(checkout_start, pattern="^checkout$"),
                      CallbackQueryHandler(buy_now, pattern=r"^buy:\d+$")],
        states={S_NAME:[MessageHandler(filters.TEXT&~filters.COMMAND, o_name)],
                S_PHONE:[MessageHandler(filters.TEXT&~filters.COMMAND, o_phone)],
                S_ADDR:[MessageHandler(filters.TEXT&~filters.COMMAND, o_done)]},
        fallbacks=[CallbackQueryHandler(o_cancel, pattern="^(home|cart)$")], per_message=False)

    add_prod = ConversationHandler(
        entry_points=[CallbackQueryHandler(a_add_start, pattern="^a:add$")],
        states={A_NAME:[MessageHandler(filters.TEXT&~filters.COMMAND, a_name)],
                A_PRICE:[MessageHandler(filters.TEXT&~filters.COMMAND, a_price)],
                A_DESC:[MessageHandler(filters.TEXT&~filters.COMMAND, a_desc)],
                A_VOL:[MessageHandler(filters.TEXT&~filters.COMMAND, a_vol)],
                A_NOTES:[MessageHandler(filters.TEXT&~filters.COMMAND, a_notes)],
                A_GENDER:[CallbackQueryHandler(a_gender, pattern="^g:")],
                A_CAT:[CallbackQueryHandler(a_cat, pattern="^sc:"), MessageHandler(filters.TEXT&~filters.COMMAND, a_cat)],
                A_PHOTO:[MessageHandler(filters.PHOTO, a_photo), MessageHandler(filters.TEXT&~filters.COMMAND, a_photo)]},
        fallbacks=[CallbackQueryHandler(o_cancel, pattern="^a:home$")], per_message=False)

    edit_prod = ConversationHandler(
        entry_points=[CallbackQueryHandler(ae_start, pattern=r"^ae:\d+$")],
        states={E_FIELD:[CallbackQueryHandler(ae_field, pattern="^ef:")],
                E_VAL:[MessageHandler(filters.TEXT&~filters.COMMAND, ae_val)]},
        fallbacks=[CallbackQueryHandler(o_cancel, pattern="^a:prods$")], per_message=False)

    photo_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(aph_start, pattern=r"^aph:\d+$")],
        states={PH:[MessageHandler(filters.PHOTO, aph_recv), MessageHandler(filters.TEXT&~filters.COMMAND, aph_recv)]},
        fallbacks=[CallbackQueryHandler(o_cancel, pattern="^a:home$")], per_message=False)

    cat_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(ac_start, pattern="^a:addcat$")],
        states={CN:[MessageHandler(filters.TEXT&~filters.COMMAND, ac_name)],
                CE:[MessageHandler(filters.TEXT&~filters.COMMAND, ac_emoji)]},
        fallbacks=[CallbackQueryHandler(o_cancel, pattern="^a:home$")], per_message=False)

    promo_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(ap_start, pattern="^a:addpromo$")],
        states={PA_TITLE:[MessageHandler(filters.TEXT&~filters.COMMAND, ap_title)],
                PA_DESC:[MessageHandler(filters.TEXT&~filters.COMMAND, ap_desc)]},
        fallbacks=[CallbackQueryHandler(o_cancel, pattern="^a:home$")], per_message=False)

    bcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(bc_start, pattern="^a:bcast$")],
        states={BC:[MessageHandler(filters.TEXT&~filters.COMMAND, bc_send)]},
        fallbacks=[CallbackQueryHandler(o_cancel, pattern="^a:home$")], per_message=False)

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("admin", cmd_admin))
    for c in [checkout, add_prod, edit_prod, photo_conv, cat_conv, promo_conv, bcast_conv]:
        app.add_handler(c)
    app.add_handler(CallbackQueryHandler(router))

    logging.info(f"🚀 {SHOP} запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
