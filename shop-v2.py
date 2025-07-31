import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

TOKEN = '8417311694:AAGnD82Str6vjudpm7ia77cG-HvyIk01mlQ'
ADMIN_CHAT_ID = 5180138277  # Ваш ID в Telegram
PRICE_PER_DEVICE = 50  # Цена за одно устройство

# База данных ссылок
LINKS_DATABASE = {
    '1': ['https://drive.google.com/1dev1', 'https://drive.google.com/1dev2'],
    '2': ['https://drive.google.com/2dev1', 'https://drive.google.com/2dev2'],
    '3': ['https://drive.google.com/3dev1'],
    '4': ['https://drive.google.com/4dev1'],
    '5': ['https://drive.google.com/5dev1', 'https://drive.google.com/5dev3']
}

# Файл для хранения использованных ссылок
USED_LINKS_FILE = 'used_links.txt'

def load_used_links():
    """Загрузка использованных ссылок из файла"""
    if not os.path.exists(USED_LINKS_FILE):
        return set()
    
    with open(USED_LINKS_FILE, 'r') as f:
        return set(line.strip() for line in f if line.strip())

def save_used_link(link):
    """Сохранение использованной ссылки"""
    with open(USED_LINKS_FILE, 'a') as f:
        f.write(f"{link}\n")

def get_available_links(count):
    """Получение доступных ссылок для указанного количества"""
    used_links = load_used_links()
    return [link for link in LINKS_DATABASE.get(count, []) if link not in used_links]

def is_admin(user_id):
    return user_id == ADMIN_CHAT_ID

def get_devices_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{i} устройств — {PRICE_PER_DEVICE*i}₽", callback_data=str(i))]
        for i in range(1, 6)
    ])

def get_admin_keyboard(user_id, count):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить оплату", callback_data=f"approve_{user_id}_{count}")],
        [InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user_id}")]
    ])

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🛒 *Бот продажи лицензий*\n\n"
        f"💰 Цена: {PRICE_PER_DEVICE}₽ за устройство\n"
        "👇 Выберите количество устройств:",
        reply_markup=get_devices_keyboard(),
        parse_mode="Markdown"
    )

def process_device_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    count = query.data
    total = int(count) * PRICE_PER_DEVICE
    
    context.user_data['selected_devices'] = count
    
    query.edit_message_text(
        f"🔢 *Выбрано:* {count} устройств\n"
        f"💵 *К оплате:* {total}₽\n\n"
        "💳 *Реквизиты для оплаты:*\n"
        "Карта: `2200 7012 3478 7676 `\n\n"
        "📤 После оплаты отправьте скриншот чека",
        parse_mode="Markdown"
    )

def handle_payment_proof(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    count = context.user_data.get('selected_devices', '1')
    username = update.message.from_user.username or f"id{user_id}"
    
    admin_message = (
        f"🆕 *Новый заказ*\n\n"
        f"👤 Покупатель: @{username}\n"
        f"📱 Устройств: {count}\n"
        f"💸 Сумма: {int(count)*PRICE_PER_DEVICE}₽"
    )
    
    if update.message.photo:
        update.message.forward(ADMIN_CHAT_ID)
        context.bot.send_message(
            ADMIN_CHAT_ID,
            admin_message,
            reply_markup=get_admin_keyboard(user_id, count),
            parse_mode="Markdown"
        )
    else:
        context.bot.send_message(
            ADMIN_CHAT_ID,
            f"{admin_message}\n✉️ Комментарий: {update.message.text}",
            reply_markup=get_admin_keyboard(user_id, count),
            parse_mode="Markdown"
        )
    
    update.message.reply_text("⌛ Ваш платеж передан на проверку. Ожидайте ссылку!")

def process_admin_decision(update: Update, context: CallbackContext):
    query = update.callback_query
    action, *data = query.data.split('_')
    
    if not is_admin(query.from_user.id):
        query.answer("🚫 Только для администратора!", show_alert=True)
        return
    
    if action == "reject":
        user_id = data[0]
        context.bot.send_message(
            user_id, 
            "❌ Ваш платеж был отклонен администратором\n"
            "💰 Средства будут возвращены в течение 24 часов"
        )
        query.edit_message_text(f"❌ Заказ {user_id} отклонен")
        return
    
    # Подтверждение оплаты
    user_id = data[0]
    count = data[1]
    available_links = get_available_links(count)
    
    if not available_links:
        # Нет доступных ссылок
        query.answer("⚠ Нет доступных ссылок!", show_alert=True)
        context.bot.send_message(
            user_id,
            "⚠ На данный момент нет доступных ссылок для вашего заказа\n"
            "💰 Средства будут возвращены в течение 24 часов\n"
            "🔄 Пожалуйста, попробуйте позже или свяжитесь с поддержкой"
        )
        query.edit_message_text(
            f"⚠ Для пользователя {user_id} нет доступных ссылок ({count} устройств)\n"
            "💰 Инициирован возврат средств"
        )
        return
    
    # Получаем первую доступную ссылку
    download_link = available_links[0]
    
    # Сохраняем ссылку как использованную
    save_used_link(download_link)
    
    # Отправляем ссылку покупателю
    context.bot.send_message(
        user_id,
        f"🎉 *Ваша ссылка для скачивания!*\n\n"
        f"🔗 {download_link}\n\n"
        f"📦 Количество устройств: {count}\n"
        f"📌 Ссылка одноразовая и привязана к вашему аккаунту",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    
    query.edit_message_text(f"✅ Пользователь {user_id} получил ссылку")

def admin_add_links(update: Update, context: CallbackContext):
    if not is_admin(update.message.from_user.id):
        update.message.reply_text("🚫 Недостаточно прав!")
        return
    
    if len(context.args) < 2:
        update.message.reply_text("ℹ️ Использование: /addlinks КОЛИЧЕСТВО ССЫЛКА1 ССЫЛКА2 ...")
        return
    
    count = context.args[0]
    new_links = context.args[1:]
    
    if count not in LINKS_DATABASE:
        LINKS_DATABASE[count] = []
    
    LINKS_DATABASE[count].extend(new_links)
    update.message.reply_text(f"✅ Добавлено {len(new_links)} ссылок для {count} устройств")

def admin_check_links(update: Update, context: CallbackContext):
    if not is_admin(update.message.from_user.id):
        update.message.reply_text("🚫 Недостаточно прав!")
        return
    
    message = "📊 Доступные ссылки:\n\n"
    for count in sorted(LINKS_DATABASE.keys()):
        available = len(get_available_links(count))
        total = len(LINKS_DATABASE[count])
        message += f"• {count} устройств: {available}/{total} (доступно/всего)\n"
    
    update.message.reply_text(message)

def main():
    # Создаем файл для использованных ссылок, если его нет
    if not os.path.exists(USED_LINKS_FILE):
        open(USED_LINKS_FILE, 'w').close()
    
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("addlinks", admin_add_links))
    dp.add_handler(CommandHandler("links", admin_check_links))
    
    dp.add_handler(CallbackQueryHandler(process_device_selection, pattern=r'^[1-5]$'))
    dp.add_handler(CallbackQueryHandler(process_admin_decision, pattern=r'^(approve|reject)_\d+(_\d+)?$'))
    
    dp.add_handler(MessageHandler(Filters.text | Filters.photo, handle_payment_proof))
    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()