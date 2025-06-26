from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
from telegram.error import TelegramError
import logging

# Logging sozlamalari
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot tokeni va kanal ID
TOKEN = "7795753797:AAF97ku5-weFRMISUMfAYI1YfxVx5wOz7u0"
ADMIN_ID = 6631973071
CHANNEL_ID = -1002782890597  # Kanal ID'si -100 bilan boshlanishi kerak

# Xabarni saqlash uchun vaqtinchalik ombor
pending_messages = {}

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Salom! Xabar yuboring (matn, rasm, fayl yoki video), u admin tomonidan ko'rib chiqiladi.")

def handle_message(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    chat_id = update.message.chat_id
    message_id = update.message.message_id

    # Xabarni admin uchun tayyorlash
    message_data = {
        'user_id': user.id,
        'chat_id': chat_id,
        'message_id': message_id,
        'content': {}
    }

    # Xabar turini aniqlash
    if update.message.text:
        message_data['content']['text'] = update.message.text
    if update.message.photo:
        message_data['content']['photo'] = update.message.photo[-1].file_id
        message_data['content']['caption'] = update.message.caption or ""
    if update.message.document:
        message_data['content']['document'] = update.message.document.file_id
        message_data['content']['caption'] = update.message.caption or ""
    if update.message.video:
        message_data['content']['video'] = update.message.video.file_id
        message_data['content']['caption'] = update.message.caption or ""

    # Xabarni pending_messages ga saqlash
    pending_messages[message_id] = message_data

    # Admin uchun tugmalar
    keyboard = [
        [
            InlineKeyboardButton("Tasdiqlash ✅", callback_data=f"approve_{message_id}"),
            InlineKeyboardButton("Rad etish ❌", callback_data=f"reject_{message_id}"),
            InlineKeyboardButton("Tahrirlash ✏️", callback_data=f"edit_{message_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Xabarni adminga yuborish
    admin_message = f"Yangi xabar foydalanuvchidan: {user.first_name} (ID: {user.id})\n"
    if 'text' in message_data['content']:
        admin_message += f"Matn: {message_data['content']['text']}\n"
    if 'photo' in message_data['content']:
        context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=message_data['content']['photo'],
            caption=admin_message + f"Caption: {message_data['content']['caption']}",
            reply_markup=reply_markup
        )
    elif 'document' in message_data['content']:
        context.bot.send_document(
            chat_id=ADMIN_ID,
            document=message_data['content']['document'],
            caption=admin_message + f"Caption: {message_data['content']['caption']}",
            reply_markup=reply_markup
        )
    elif 'video' in message_data['content']:
        context.bot.send_video(
            chat_id=ADMIN_ID,
            video=message_data['content']['video'],
            caption=admin_message + f"Caption: {message_data['content']['caption']}",
            reply_markup=reply_markup
        )
    else:
        context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            reply_markup=reply_markup
        )

    update.message.reply_text("Xabaringiz adminga yuborildi. Tasdiqlanishini kuting.")

def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    action, message_id = query.data.split('_')
    message_id = int(message_id)

    if message_id not in pending_messages:
        query.message.reply_text("Xabar topilmadi yoki allaqachon qayta ishlangan.")
        return

    message_data = pending_messages[message_id]

    if action == "approve":
        try:
            # Xabarni kanalga yuborish
            if 'photo' in message_data['content']:
                context.bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=message_data['content']['photo'],
                    caption=message_data['content']['caption']
                )
            elif 'document' in message_data['content']:
                context.bot.send_document(
                    chat_id=CHANNEL_ID,
                    document=message_data['content']['document'],
                    caption=message_data['content']['caption']
                )
            elif 'video' in message_data['content']:
                context.bot.send_video(
                    chat_id=CHANNEL_ID,
                    video=message_data['content']['video'],
                    caption=message_data['content']['caption']
                )
            elif 'text' in message_data['content']:
                context.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=message_data['content']['text']
                )

            # Foydalanuvchiga xabar
            context.bot.send_message(
                chat_id=message_data['chat_id'],
                text="Xabaringiz tasdiqlandi va kanalga joylandi!"
            )
            query.message.reply_text("Xabar tasdiqlandi va kanalga yuborildi.")
        except TelegramError as e:
            query.message.reply_text(f"Xatolik yuz berdi: {e}")

        # Xabarni o'chirish
        del pending_messages[message_id]

    elif action == "reject":
        context.bot.send_message(
            chat_id=message_data['chat_id'],
            text="Xabaringiz rad etildi."
        )
        query.message.reply_text("Xabar rad etildi.")
        del pending_messages[message_id]

    elif action == "edit":
        query.message.reply_text("Iltimos, tahrirlangan xabar matnini yuboring.")
        context.user_data['editing_message_id'] = message_id

def handle_edit(update: Update, context: CallbackContext) -> None:
    if 'editing_message_id' not in context.user_data:
        return

    message_id = context.user_data['editing_message_id']
    if message_id not in pending_messages:
        update.message.reply_text("Xabar topilmadi.")
        return

    message_data = pending_messages[message_id]
    new_text = update.message.text

    # Tahrirlangan matnni yangilash
    message_data['content']['text'] = new_text
    if 'caption' in message_data['content']:
        message_data['content']['caption'] = new_text

    # Admin uchun yangilangan xabarni qayta yuborish
    keyboard = [
        [
            InlineKeyboardButton("Tasdiqlash ✅", callback_data=f"approve_{message_id}"),
            InlineKeyboardButton("Rad etish ❌", callback_data=f"reject_{message_id}"),
            InlineKeyboardButton("Tahrirlash ✏️", callback_data=f"edit_{message_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    admin_message = f"Tahrirlangan xabar foydalanuvchidan (ID: {message_data['user_id']}):\n"
    if 'text' in message_data['content']:
        admin_message += f"Matn: {message_data['content']['text']}\n"

    if 'photo' in message_data['content']:
        context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=message_data['content']['photo'],
            caption=admin_message + f"Caption: {message_data['content']['caption']}",
            reply_markup=reply_markup
        )
    elif 'document' in message_data['content']:
        context.bot.send_document(
            chat_id=ADMIN_ID,
            document=message_data['content']['document'],
            caption=admin_message + f"Caption: {message_data['content']['caption']}",
            reply_markup=reply_markup
        )
    elif 'video' in message_data['content']:
        context.bot.send_video(
            chat_id=ADMIN_ID,
            video=message_data['content']['video'],
            caption=admin_message + f"Caption: {message_data['content']['caption']}",
            reply_markup=reply_markup
        )
    else:
        context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            reply_markup=reply_markup
        )

    update.message.reply_text("Xabar tahrirlandi va qayta adminga yuborildi.")
    del context.user_data['editing_message_id']

def main() -> None:
    # Updater obyektini yaratish
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Buyruqlar
    dp.add_handler(CommandHandler("start", start))

    # Xabarlar (matn, rasm, fayl, video)
    dp.add_handler(MessageHandler(Filters.text | Filters.photo | Filters.document | Filters.video, handle_message))

    # Tugma bosish
    dp.add_handler(CallbackQueryHandler(button_callback))

    # Tahrirlangan xabar
    dp.add_handler(MessageHandler(Filters.text & Filters.chat(ADMIN_ID), handle_edit))

    # Botni ishga tushirish
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
