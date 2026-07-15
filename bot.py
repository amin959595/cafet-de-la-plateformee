import telebot
from telebot import types
import time
import json
import os

# Вставь сюда НОВЫЙ токен от BotFather
# Клиентская часть — на французском, админ-панель — на русском
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

# Вставь сюда свой Telegram ID
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
if ADMIN_ID == 0:
    raise RuntimeError("ADMIN_ID is not set")

bot = telebot.TeleBot(TOKEN)

MENU_FILE = "menu_dishes.json"
PLAT_FILE = "plat_du_jour.json"
SECTIONS_FILE = "menu_sections.json"
ORDERS_FILE = "orders.json"

menu_dishes = {}
plat_du_jour = {}
menu_sections = {}
orders = {}

carts = {}
pending_orders = {}

waiting_menu_photo = set()
waiting_menu_name = {}
waiting_menu_price = {}
waiting_menu_section = {}

waiting_plat_photo = set()
waiting_plat_name = {}
waiting_plat_price = {}


def save_json(file_name, data):
    with open(file_name, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def load_json(file_name):
    if not os.path.exists(file_name):
        return {}

    try:
        with open(file_name, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}


menu_dishes = load_json(MENU_FILE)
plat_du_jour = load_json(PLAT_FILE)
menu_sections = load_json(SECTIONS_FILE)
orders = load_json(ORDERS_FILE)


def admin_main_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "🍽 Управление меню",
            callback_data="admin_menu_settings"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "⭐ Параметры Plat du Jour",
            callback_data="admin_plat_settings"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "📂 Управление разделами",
            callback_data="admin_sections"
        )
    )
    return markup


def menu_settings_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "➕ Добавить блюдо в меню",
            callback_data="add_menu_dish"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "❌ Удалить блюдо из меню",
            callback_data="delete_menu_dish"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "⬅ Назад",
            callback_data="back_to_admin"
        )
    )
    return markup


def plat_settings_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "➕ Создать блюдо",
            callback_data="make_producer"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "❌ Удалить блюдо",
            callback_data="delete_producer"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "⬅ Назад",
            callback_data="back_to_admin"
        )
    )
    return markup


def sections_settings_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "➕ Добавить раздел",
            callback_data="add_section"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "❌ Удалить раздел",
            callback_data="delete_section"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "⬅ Назад",
            callback_data="back_to_admin"
        )
    )
    return markup


def main_menu_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)

    for section_id, section_name in menu_sections.items():
        markup.add(
            types.InlineKeyboardButton(
                f" {section_name}",
                callback_data=f"open_section_{section_id}"
            )
        )

    if any(not dish.get("section_id") for dish in menu_dishes.values()):
        markup.add(
            types.InlineKeyboardButton(
                "🍽 Autres plats",
                callback_data="open_section_none"
            )
        )

    markup.add(
        types.InlineKeyboardButton(
            "🛒 Panier",
            callback_data="open_cart"
        )
    )
    return markup


def dishes_keyboard(section_id):
    markup = types.InlineKeyboardMarkup(row_width=1)

    for dish_id, dish in menu_dishes.items():
        dish_section = dish.get("section_id")

        if section_id == "none":
            match = not dish_section
        else:
            match = dish_section == section_id

        if match:
            markup.add(
                types.InlineKeyboardButton(
                    dish.get("name", "Sans nom"),
                    callback_data=f"show_menu_dish_{dish_id}"
                )
            )

    markup.add(
        types.InlineKeyboardButton(
            "🛒 Panier",
            callback_data="open_cart"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "⬅ Retour aux catégories",
            callback_data="back_to_sections"
        )
    )
    return markup


def cart_keyboard(user_id):
    markup = types.InlineKeyboardMarkup()
    cart = carts.get(user_id, [])

    for index, cart_item in enumerate(cart):
        dish, source_name = get_cart_item_data(cart_item)

        if not dish:
            continue

        name = dish.get("name", dish.get("text", "Sans nom"))
        quantity = cart_item.get("quantity", 1)

        markup.row(
            types.InlineKeyboardButton(
                "➖",
                callback_data=f"decrease_cart_{index}"
            ),
            types.InlineKeyboardButton(
                f"{name} × {quantity}",
                callback_data="ignore"
            ),
            types.InlineKeyboardButton(
                "➕",
                callback_data=f"increase_cart_{index}"
            )
        )

        markup.add(
            types.InlineKeyboardButton(
                f"❌ Retirer : {name}",
                callback_data=f"remove_cart_{index}"
            )
        )

    if cart:
        markup.add(
            types.InlineKeyboardButton(
                "✅ Commander",
                callback_data="checkout_cart"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "🗑 Vider le panier",
                callback_data="clear_cart"
            )
        )

    markup.add(
        types.InlineKeyboardButton(
            "⬅ Retour au menu",
            callback_data="back_to_sections"
        )
    )
    return markup

def get_cart_item_data(cart_item):
    source = cart_item.get("source")
    dish_id = cart_item.get("dish_id")

    if source == "plat":
        dish = plat_du_jour.get(dish_id)
        source_name = "Plat du Jour"
    else:
        dish = menu_dishes.get(dish_id)
        source_name = "Menu"

    return dish, source_name


def format_cart(user_id):
    cart = carts.get(user_id, [])

    if not cart:
        return "🛒 Votre panier est vide."

    lines = ["🛒 <b>Votre panier</b>\n"]
    total = 0.0

    for index, cart_item in enumerate(cart, start=1):
        dish, source_name = get_cart_item_data(cart_item)

        if not dish:
            continue

        name = dish.get("name", dish.get("text", "Sans nom"))
        price_text = dish.get("price", "0")
        quantity = cart_item.get("quantity", 1)

        lines.append(
            f"{index}. {name} × {quantity} — {price_text} ({source_name})"
        )

        try:
            numeric = (
                price_text.replace("€", "")
                .replace(",", ".")
                .strip()
            )
            total += float(numeric) * quantity
        except ValueError:
            pass

    if total > 0:
        lines.append(f"\n💰 Total : {total:.2f}€")

    return "\n".join(lines)

def order_details(order):
    lines = ["🧾 <b>Votre commande</b>\n"]

    if order.get("customer_name"):
        lines.append(f"👤 Nom : {order['customer_name']}")
    if order.get("pickup_time"):
        lines.append(f"🕒 Heure de retrait : {order['pickup_time']}")

    if order.get("customer_name") or order.get("pickup_time"):
        lines.append("")

    for index, item in enumerate(order.get("items", []), start=1):
        source_name = item.get("source", "")
        source_suffix = f" ({source_name})" if source_name else ""

        quantity = item.get("quantity", 1)

        lines.append(
            f"{index}. {item['name']} × {quantity} — "
            f"{item['price']}{source_suffix}"
        )

    total = order.get("total")
    if total:
        lines.append(f"\n💰 Total : {total}")

    return "\n".join(lines)


@bot.message_handler(commands=["start"])
def start(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Oui", callback_data="cb_yes"),
        types.InlineKeyboardButton("Non", callback_data="cb_no")
    )

    bot.send_message(
        message.chat.id,
        "Bonjour et bienvenue dans la Cafet de la Platforme.\n"
        "Voulez-vous passer une commande ?",
        reply_markup=markup
    )


@bot.message_handler(commands=["menu"])
def show_menu(message):
    if not menu_dishes:
        bot.send_message(
            message.chat.id,
            "❌ Le menu est vide."
        )
        return

    bot.send_message(
        message.chat.id,
        "🍽 <b>Le menu</b>\n\nChoisissez une catégorie :",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard()
    )


@bot.message_handler(commands=["plat_du_jour"])
def show_plat_du_jour(message):
    if not plat_du_jour:
        bot.send_message(
            message.chat.id,
            "❌ Il n’y a pas de Plat du Jour."
        )
        return

    for dish_id, dish in plat_du_jour.items():
        dish_name = dish.get("name", dish.get("text", "Sans nom"))
        dish_price = dish.get("price", "Prix non indiqué")

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "🛒 Commander",
                callback_data=f"add_plat_cart_{dish_id}"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "🛒 Voir le panier",
                callback_data="open_cart"
            )
        )

        bot.send_photo(
            message.chat.id,
            dish["photo"],
            caption=(
                f"⭐ <b>{dish_name}</b>\n"
                f"💰 Prix : <b>{dish_price}</b>"
            ),
            parse_mode="HTML",
            reply_markup=markup
        )


@bot.message_handler(commands=["admin"])
def admin(message):
    bot.send_message(
        message.chat.id,
        "⚙ Админ меню",
        reply_markup=admin_main_keyboard()
    )


@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id

    if call.data == "cb_yes":
        bot.send_message(
            call.message.chat.id,
            "Pour voir le plat du jour apuyer ici 👉 /plat_du_jour et \n"
            "Pour voir le menu apuyer ici 👉 /menu"
        )

    elif call.data == "cb_no":
        bot.send_message(
            call.message.chat.id,
            "Au revoir, revenez bientôt !"
        )

    elif call.data == "admin_menu_settings":
        bot.edit_message_text(
            "🍽 Управление меню",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=menu_settings_keyboard()
        )

    elif call.data == "admin_plat_settings":
        bot.edit_message_text(
            "⭐ Параметры Plat du Jour",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=plat_settings_keyboard()
        )

    elif call.data == "admin_sections":
        bot.edit_message_text(
            "📂 Управление разделами",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=sections_settings_keyboard()
        )

    elif call.data == "back_to_admin":
        bot.edit_message_text(
            "⚙ Админ меню",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_main_keyboard()
        )

    elif call.data == "add_section":
        msg = bot.send_message(
            call.message.chat.id,
            "✏️ Напиши название нового раздела."
        )
        bot.register_next_step_handler(msg, save_section_name)

    elif call.data == "delete_section":
        if not menu_sections:
            bot.send_message(
                call.message.chat.id,
                "❌ Разделов нет."
            )
            return

        markup = types.InlineKeyboardMarkup()

        for section_id, section_name in menu_sections.items():
            markup.add(
                types.InlineKeyboardButton(
                    section_name,
                    callback_data=f"del_section_{section_id}"
                )
            )

        bot.send_message(
            call.message.chat.id,
            "Выбери раздел для удаления:",
            reply_markup=markup
        )

    elif call.data.startswith("del_section_"):
        section_id = call.data.replace("del_section_", "", 1)

        if section_id in menu_sections:
            del menu_sections[section_id]

            for dish in menu_dishes.values():
                if dish.get("section_id") == section_id:
                    dish["section_id"] = None

            save_json(SECTIONS_FILE, menu_sections)
            save_json(MENU_FILE, menu_dishes)

            bot.edit_message_text(
                "✅ Раздел удалён. Блюда остались без раздела.",
                call.message.chat.id,
                call.message.message_id
            )

    elif call.data == "add_menu_dish":
        waiting_menu_photo.add(user_id)
        waiting_menu_name.pop(user_id, None)
        waiting_menu_price.pop(user_id, None)
        waiting_menu_section.pop(user_id, None)

        bot.send_message(
            call.message.chat.id,
            "📷 Отправь фото блюда."
        )

    elif call.data == "delete_menu_dish":
        if not menu_dishes:
            bot.send_message(
                call.message.chat.id,
                "❌ блюд в меню нет."
            )
            return

        markup = types.InlineKeyboardMarkup()

        for dish_id, dish in menu_dishes.items():
            markup.add(
                types.InlineKeyboardButton(
                    dish.get("name", "Sans nom"),
                    callback_data=f"del_menu_{dish_id}"
                )
            )

        bot.send_message(
            call.message.chat.id,
            "Выберите блюдо из меню для удаления:",
            reply_markup=markup
        )

    elif call.data.startswith("del_menu_"):
        dish_id = call.data.replace("del_menu_", "", 1)

        if dish_id in menu_dishes:
            del menu_dishes[dish_id]
            save_json(MENU_FILE, menu_dishes)

            bot.edit_message_text(
                "✅ блюдо удалено из меню.",
                call.message.chat.id,
                call.message.message_id
            )

    elif call.data.startswith("choose_section_"):
        section_value = call.data.replace("choose_section_", "", 1)

        if user_id not in waiting_menu_section:
            bot.send_message(
                call.message.chat.id,
                "❌ Данные блюда не найдены."
            )
            return

        dish_data = waiting_menu_section.pop(user_id)

        if section_value == "none":
            section_id = None
        else:
            section_id = section_value

        dish_id = str(int(time.time() * 1000))

        menu_dishes[dish_id] = {
            "photo": dish_data["photo"],
            "name": dish_data["name"],
            "price": dish_data["price"],
            "section_id": section_id
        }

        save_json(MENU_FILE, menu_dishes)

        bot.edit_message_text(
            f"✅ блюдо '{dish_data['name']}' добавлено в меню.",
            call.message.chat.id,
            call.message.message_id
        )

    elif call.data.startswith("open_section_"):
        section_id = call.data.replace("open_section_", "", 1)

        if section_id == "none":
            title = "🍽 Autres plats"
        else:
            title = f"📂 {menu_sections.get(section_id, 'Раздел')}"

        bot.edit_message_text(
            f"{title}\n\nВыберите блюдо:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=dishes_keyboard(section_id)
        )

    elif call.data == "back_to_sections":
        bot.edit_message_text(
            "🍽 <b>Le menu</b>\n\nChoisissez une catégorie :",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=main_menu_keyboard()
        )

    elif call.data.startswith("show_menu_dish_"):
        dish_id = call.data.replace("show_menu_dish_", "", 1)
        dish = menu_dishes.get(dish_id)

        if not dish:
            bot.send_message(
                call.message.chat.id,
                "❌ Plat introuvable."
            )
            return

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "➕ Ajouter au panier",
                callback_data=f"add_cart_{dish_id}"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "🛒 Voir le panier",
                callback_data="open_cart"
            )
        )

        bot.send_photo(
            call.message.chat.id,
            dish["photo"],
            caption=(
                f"🍽 <b>{dish['name']}</b>\n"
                f"💰 Prix : <b>{dish['price']}</b>"
            ),
            parse_mode="HTML",
            reply_markup=markup
        )

    elif call.data.startswith("add_cart_"):
        dish_id = call.data.replace("add_cart_", "", 1)

        if dish_id not in menu_dishes:
            bot.send_message(
                call.message.chat.id,
                "❌ Plat introuvable."
            )
            return

        cart = carts.setdefault(user_id, [])
        existing_item = next(
            (
                item for item in cart
                if item.get("source") == "menu"
                and item.get("dish_id") == dish_id
            ),
            None
        )

        if existing_item:
            existing_item["quantity"] = existing_item.get("quantity", 1) + 1
        else:
            cart.append({
                "source": "menu",
                "dish_id": dish_id,
                "quantity": 1
            })

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "➕ Continuer la commande",
                callback_data="continue_after_menu"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "✅ Commander",
                callback_data="checkout_cart"
            )
        )

        bot.send_message(
            call.message.chat.id,
            "✅ Ajouté avec succès !",
            reply_markup=markup
        )

    elif call.data.startswith("add_plat_cart_"):
        dish_id = call.data.replace("add_plat_cart_", "", 1)

        if dish_id not in plat_du_jour:
            bot.send_message(
                call.message.chat.id,
                "❌ Plat du Jour introuvable."
            )
            return

        cart = carts.setdefault(user_id, [])
        existing_item = next(
            (
                item for item in cart
                if item.get("source") == "plat"
                and item.get("dish_id") == dish_id
            ),
            None
        )

        if existing_item:
            existing_item["quantity"] = existing_item.get("quantity", 1) + 1
        else:
            cart.append({
                "source": "plat",
                "dish_id": dish_id,
                "quantity": 1
            })

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "➕ Continuer la commande",
                callback_data="continue_after_plat"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "✅ Commander",
                callback_data="checkout_cart"
            )
        )

        bot.send_message(
            call.message.chat.id,
            "✅ Ajouté avec succès !",
            reply_markup=markup
        )

    elif call.data == "continue_after_menu":
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "⭐ Voir le Plat du Jour",
                callback_data="show_plat_after_menu"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "🍽 Continuer dans le menu",
                callback_data="back_to_sections"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "🛒 Voir le panier",
                callback_data="open_cart"
            )
        )

        bot.edit_message_text(
            "Voulez-vous aussi commander quelque chose du Plat du Jour ?",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )

    elif call.data == "continue_after_plat":
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "🍽 Voir le menu",
                callback_data="back_to_sections"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "⭐ Continuer avec le Plat du Jour",
                callback_data="show_plat_after_menu"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "🛒 Voir le panier",
                callback_data="open_cart"
            )
        )

        bot.edit_message_text(
            "Voulez-vous aussi commander quelque chose dans le menu ?",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )

    elif call.data == "show_plat_after_menu":
        if not plat_du_jour:
            bot.send_message(
                call.message.chat.id,
                "❌ Il n’y a pas de Plat du Jour."
            )
            return

        for dish_id, dish in plat_du_jour.items():
            dish_name = dish.get("name", dish.get("text", "Sans nom"))
            dish_price = dish.get("price", "Prix non indiqué")

            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(
                    "🛒 Commander",
                    callback_data=f"add_plat_cart_{dish_id}"
                )
            )

            bot.send_photo(
                call.message.chat.id,
                dish["photo"],
                caption=(
                    f"⭐ <b>{dish_name}</b>\n"
                    f"💰 Prix : <b>{dish_price}</b>"
                ),
                parse_mode="HTML",
                reply_markup=markup
            )

    elif call.data == "open_cart":
        try:
            bot.edit_message_text(
                format_cart(user_id),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="HTML",
                reply_markup=cart_keyboard(user_id)
            )
        except telebot.apihelper.ApiTelegramException:
            bot.send_message(
                call.message.chat.id,
                format_cart(user_id),
                parse_mode="HTML",
                reply_markup=cart_keyboard(user_id)
            )

    elif call.data == "ignore":
        return

    elif call.data.startswith("increase_cart_"):
        try:
            item_index = int(call.data.replace("increase_cart_", "", 1))
        except ValueError:
            return

        cart = carts.get(user_id, [])

        if 0 <= item_index < len(cart):
            cart[item_index]["quantity"] = cart[item_index].get("quantity", 1) + 1

        bot.edit_message_text(
            format_cart(user_id),
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=cart_keyboard(user_id)
        )

    elif call.data.startswith("decrease_cart_"):
        try:
            item_index = int(call.data.replace("decrease_cart_", "", 1))
        except ValueError:
            return

        cart = carts.get(user_id, [])

        if 0 <= item_index < len(cart):
            current_quantity = cart[item_index].get("quantity", 1)

            if current_quantity > 1:
                cart[item_index]["quantity"] = current_quantity - 1
            else:
                cart.pop(item_index)

        bot.edit_message_text(
            format_cart(user_id),
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=cart_keyboard(user_id)
        )

    elif call.data.startswith("remove_cart_"):
        try:
            item_index = int(call.data.replace("remove_cart_", "", 1))
        except ValueError:
            return

        cart = carts.get(user_id, [])

        if 0 <= item_index < len(cart):
            cart.pop(item_index)

        bot.edit_message_text(
            format_cart(user_id),
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=cart_keyboard(user_id)
        )

    elif call.data == "clear_cart":
        carts[user_id] = []

        bot.edit_message_text(
            "🗑 Votre panier a été vidé.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=cart_keyboard(user_id)
        )

    elif call.data == "checkout_cart":
        cart = carts.get(user_id, [])

        if not cart:
            bot.send_message(
                call.message.chat.id,
                "❌ Votre panier est vide."
            )
            return

        pending_orders[user_id] = {
            "chat_id": call.message.chat.id,
            "items_ids": list(cart),
            "step": "name"
        }

        bot.send_message(
            call.message.chat.id,
            "👤 Quel est votre nom ?"
        )

    elif call.data.startswith("view_order_"):
        order_id = call.data.replace("view_order_", "", 1)
        order = orders.get(order_id)

        if not order:
            bot.send_message(
                call.message.chat.id,
                "❌ Commande introuvable."
            )
            return

        bot.send_message(
            call.message.chat.id,
            order_details(order),
            parse_mode="HTML"
        )

    elif call.data == "make_producer":
        waiting_plat_photo.add(user_id)
        waiting_plat_name.pop(user_id, None)
        waiting_plat_price.pop(user_id, None)

        bot.send_message(
            call.message.chat.id,
            "📷 Отправь фото блюда дня."
        )

    elif call.data == "delete_producer":
        if not plat_du_jour:
            bot.send_message(
                call.message.chat.id,
                "❌ блюд нет."
            )
            return

        markup = types.InlineKeyboardMarkup()

        for dish_id, dish in plat_du_jour.items():
            dish_name = dish.get("name", dish.get("text", "Sans nom"))

            markup.add(
                types.InlineKeyboardButton(
                    dish_name,
                    callback_data=f"del_plat_{dish_id}"
                )
            )

        bot.send_message(
            call.message.chat.id,
            "Выберите блюдо для удаления:",
            reply_markup=markup
        )

    elif call.data.startswith("del_plat_"):
        dish_id = call.data.replace("del_plat_", "", 1)

        if dish_id in plat_du_jour:
            del plat_du_jour[dish_id]
            save_json(PLAT_FILE, plat_du_jour)

            bot.edit_message_text(
                "✅ блюдо удалён.",
                call.message.chat.id,
                call.message.message_id
            )


def save_section_name(message):
    section_name = message.text.strip()

    if not section_name:
        bot.send_message(
            message.chat.id,
            "❌ Название раздела не может быть пустым."
        )
        return

    section_id = str(int(time.time() * 1000))
    menu_sections[section_id] = section_name
    save_json(SECTIONS_FILE, menu_sections)

    bot.send_message(
        message.chat.id,
        f"✅ Раздел '{section_name}' создан."
    )


@bot.message_handler(content_types=["photo"])
def save_photo(message):
    user_id = message.from_user.id
    photo_id = message.photo[-1].file_id

    if user_id in waiting_menu_photo:
        waiting_menu_photo.remove(user_id)

        waiting_menu_name[user_id] = {
            "photo": photo_id
        }

        bot.send_message(
            message.chat.id,
            "✏️ Теперь напиши название блюда."
        )
        return

    if user_id in waiting_plat_photo:
        waiting_plat_photo.remove(user_id)

        waiting_plat_name[user_id] = {
            "photo": photo_id
        }

        bot.send_message(
            message.chat.id,
            "✏️ Теперь напиши название блюда дня."
        )


@bot.message_handler(content_types=["text"])
def save_text_steps(message):
    user_id = message.from_user.id
    text = message.text.strip()

    if user_id in pending_orders:
        pending = pending_orders[user_id]

        if pending.get("step") == "name":
            if not text:
                bot.send_message(
                    message.chat.id,
                    "❌ Le nom ne peut pas être vide."
                )
                return

            pending["customer_name"] = text
            pending["step"] = "pickup_time"

            bot.send_message(
                message.chat.id,
                "🕒 À quelle heure souhaitez-vous récupérer votre commande ?\n\n"
                "Exemple : 12h30"
            )
            return

        if pending.get("step") == "pickup_time":
            if not text:
                bot.send_message(
                    message.chat.id,
                    "❌ L’heure ne peut pas être vide."
                )
                return

            pending["pickup_time"] = text

            items = []
            total_value = 0.0

            for cart_item in pending.get("items_ids", []):
                dish, source_name = get_cart_item_data(cart_item)

                if not dish:
                    continue

                item_name = dish.get("name", dish.get("text", "Sans nom"))
                item_price = dish.get("price", "0")
                quantity = cart_item.get("quantity", 1)

                items.append(
                    {
                        "name": item_name,
                        "price": item_price,
                        "source": source_name,
                        "quantity": quantity
                    }
                )

                try:
                    numeric = (
                        item_price
                        .replace("€", "")
                        .replace(",", ".")
                        .strip()
                    )
                    total_value += float(numeric) * quantity
                except ValueError:
                    pass

            order_id = str(int(time.time() * 1000))

            order = {
                "user_id": user_id,
                "username": message.from_user.username or "",
                "telegram_first_name": message.from_user.first_name or "",
                "customer_name": pending["customer_name"],
                "pickup_time": pending["pickup_time"],
                "items": items,
                "total": f"{total_value:.2f}€" if total_value > 0 else ""
            }

            orders[order_id] = order
            save_json(ORDERS_FILE, orders)

            carts[user_id] = []
            del pending_orders[user_id]

            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(
                    "🧾 Voir ma commande",
                    callback_data=f"view_order_{order_id}"
                )
            )
            markup.add(
                types.InlineKeyboardButton(
                    "🍽 Retour au menu",
                    callback_data="back_to_sections"
                )
            )

            bot.send_message(
                message.chat.id,
                (
                    "✅ Votre commande a bien été envoyée !\n\n"
                    f"👤 Nom : {order['customer_name']}\n"
                    f"🕒 Heure de retrait : {order['pickup_time']}"
                ),
                reply_markup=markup
            )

            admin_text = (
                "🆕 <b>NOUVELLE COMMANDE</b>\n\n"
                f"👤 Nom du client : {order['customer_name']}\n"
                f"🕒 Heure de retrait : {order['pickup_time']}\n"
                f"🔗 Username : @{order['username'] if order['username'] else 'aucun'}\n"
                f"🆔 ID Telegram : {user_id}\n\n"
                f"{order_details(order)}"
            )

            try:
                bot.send_message(
                    ADMIN_ID,
                    admin_text,
                    parse_mode="HTML"
                )
            except Exception:
                bot.send_message(
                    message.chat.id,
                    "⚠️ La commande est enregistrée, mais le message à l’administrateur n’a pas pu être envoyé."
                )

            return

    if user_id in waiting_plat_name:
        photo_data = waiting_plat_name.pop(user_id)

        waiting_plat_price[user_id] = {
            "photo": photo_data["photo"],
            "name": text
        }

        bot.send_message(
            message.chat.id,
            "💰 Теперь напиши цену блюда дня."
        )
        return

    if user_id in waiting_plat_price:
        dish_data = waiting_plat_price.pop(user_id)
        dish_id = str(int(time.time() * 1000))

        plat_du_jour[dish_id] = {
            "photo": dish_data["photo"],
            "name": dish_data["name"],
            "price": text
        }

        save_json(PLAT_FILE, plat_du_jour)

        bot.send_message(
            message.chat.id,
            f"✅ блюдо дня '{dish_data['name']}' создано.\n"
            f"💰 Цена: {text}"
        )
        return

    if user_id in waiting_menu_name:
        photo_data = waiting_menu_name.pop(user_id)

        waiting_menu_price[user_id] = {
            "photo": photo_data["photo"],
            "name": text
        }

        bot.send_message(
            message.chat.id,
            "💰 Теперь напиши цену."
        )
        return

    if user_id in waiting_menu_price:
        dish_data = waiting_menu_price.pop(user_id)

        waiting_menu_section[user_id] = {
            "photo": dish_data["photo"],
            "name": dish_data["name"],
            "price": text
        }

        markup = types.InlineKeyboardMarkup()

        for section_id, section_name in menu_sections.items():
            markup.add(
                types.InlineKeyboardButton(
                    section_name,
                    callback_data=f"choose_section_{section_id}"
                )
            )

        markup.add(
            types.InlineKeyboardButton(
                "Без раздела",
                callback_data="choose_section_none"
            )
        )

        bot.send_message(
            message.chat.id,
            "📂 Выбери раздел для блюда или нажми «Без раздела».",
            reply_markup=markup
        )


print("Бот запущен")
bot.infinity_polling(skip_pending=True)