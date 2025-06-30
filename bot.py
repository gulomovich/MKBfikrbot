import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.client.default import DefaultBotProperties

# Config
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))


# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Bot setup
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# States
class Form(StatesGroup):
    waiting = State()  
    collecting = State()  
    action = State()  
    admin_edit = State()


user_buffers = {}
user_media_groups = {}  


def get_main_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📝 Yangi taklif")]],
        resize_keyboard=True
    )
    return keyboard

def get_action_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Yuborish", callback_data="send"),
         InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")]
    ])
    return keyboard, "Ma'lumotlar qabul qilindi." 

def get_admin_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve:{user_id}"),
         InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"edit:{user_id}"),
         InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject:{user_id}")]
    ])

# Yordamchi funksiya: Tugmalarni va bog'liq xabarni o'chirish
async def remove_buttons(chat_id: int, state: FSMContext):
    user_data = await state.get_data()
    last_msg_id = user_data.get("last_message_id")
    if last_msg_id:
        try:
            # Tugmalar bilan birga xabarni o'chirish
            await bot.delete_message(chat_id=chat_id, message_id=last_msg_id)
            logging.info(f"Xabar va tugmalar o'chirildi: chat_id={chat_id}, message_id={last_msg_id}")
        except Exception as e:
            logging.warning(f"Xabar va tugmalarni o'chirishda xato: chat_id={chat_id}, message_id={last_msg_id}, xato={e}")
        finally:
            await state.update_data(last_message_id=None)

# Start
@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.set_state(Form.waiting)
    await message.answer("Botga xush kelibsiz! Yangi taklif yuborish uchun quyidagi tugmani bosing:", 
                        reply_markup=get_main_menu())


# Yangi taklif tugmasi
@dp.message(Form.waiting, F.text == "📝 Yangi taklif")
async def new_proposal(message: Message, state: FSMContext):
    await state.set_state(Form.collecting)
    user_buffers[message.from_user.id] = {"photos": [], "videos": [], "docs": [], "texts": [], "user_info": {}}
    await state.update_data(last_message_id=None)
    await message.answer("O'z taklifingizni rasm,vedio,file,matn to'rinishida yuboring.", 
                        reply_markup=types.ReplyKeyboardRemove())


# Handle content (Media Group yoki alohida kontent)
@dp.message(Form.collecting, F.content_type.in_(['photo', 'video', 'document', 'text']) | F.media_group_id)
async def handle_content(message: Message, state: FSMContext):
    user_id = message.from_user.id
    buf = user_buffers.get(user_id, {"photos": [], "videos": [], "docs": [], "texts": [], "user_info": {}})

    # Foydalanuvchi ma'lumotlarini saqlash
    buf['user_info'] = {
        'full_name': message.from_user.full_name,
        'username': message.from_user.username or 'Nomalum'
    }

    try:
        # Media guruhni aniqlash
        media_group_id = message.media_group_id
        if media_group_id:
            # Media guruh xabarni qayta ishlash
            if user_id not in user_media_groups:
                user_media_groups[user_id] = {}
            if media_group_id not in user_media_groups[user_id]:
                user_media_groups[user_id][media_group_id] = []
            user_media_groups[user_id][media_group_id].append(message.message_id)

            # Media guruhda dokumentlar qabul qilinmaydi
            if message.document:
                await message.answer("Media guruhida fayllar qo'llab-quvvatlanmaydi. Iltimos, fayllarni alohida yuboring.")
                return
            if message.photo:
                buf['photos'].append(message.photo[-1].file_id)
            elif message.video:
                buf['videos'].append(message.video.file_id)

            user_buffers[user_id] = buf

            # Media guruhning oxirgi xabari ekanligini tekshirish uchun qisqa kutish
            await asyncio.sleep(0.5)  # 0.5 sekund kutish, guruh xabarlari to'liq kelishi uchun
            current_group_messages = user_media_groups.get(user_id, {}).get(media_group_id, [])
            if message.message_id == max(current_group_messages):  # Eng katta message_id oxirgi xabar deb hisoblanadi
                await state.set_state(Form.action)
                await remove_buttons(message.chat.id, state)
                keyboard, text = get_action_keyboard()  # Tugmalar va xabar
                msg = await bot.send_message(
                    chat_id=message.chat.id,
                    text=text,
                    reply_markup=keyboard
                )
                await state.update_data(last_message_id=msg.message_id)
                logging.info(f"Action tugmalari yuborildi: chat_id={message.chat.id}, message_id={msg.message_id}")
                # Media guruhni tozalash
                user_media_groups[user_id].pop(media_group_id, None)
        else:
            # Alohida kontentni qayta ishlash (dokumentlar ruxsat etiladi)
            if message.photo:
                buf['photos'].append(message.photo[-1].file_id)
            elif message.video:
                buf['videos'].append(message.video.file_id)
            elif message.document:
                buf['docs'].append(message.document.file_id)
            elif message.text:
                buf['texts'].append(message.html_text)

            user_buffers[user_id] = buf
            await state.set_state(Form.action)
            await remove_buttons(message.chat.id, state)
            keyboard, text = get_action_keyboard()  # Tugmalar va xabar
            msg = await bot.send_message(
                chat_id=message.chat.id,
                text=text,
                reply_markup=keyboard
            )
            await state.update_data(last_message_id=msg.message_id)
            logging.info(f"Action tugmalari yuborildi: chat_id={message.chat.id}, message_id={msg.message_id}")
    except Exception as e:
        logging.error(f"Ma'lumotni qayta ishlashda xato: user_id={user_id}, xato={e}")
        await message.answer("Ma'lumotni qabul qilishda xato yuz berdi. Iltimos, qayta urinib ko'ring.")

# Yana ma'lumot qo'shish uchun collecting holatiga qaytish
@dp.message(Form.action, F.content_type.in_(['photo', 'video', 'document', 'text']) | F.media_group_id)
async def continue_collecting(message: Message, state: FSMContext):
    user_id = message.from_user.id
    buf = user_buffers.get(user_id, {"photos": [], "videos": [], "docs": [], "texts": [], "user_info": {}})

    # Foydalanuvchi ma'lumotlarini saqlash
    buf['user_info'] = {
        'full_name': message.from_user.full_name,
        'username': message.from_user.username or 'Nomalum'
    }

    await remove_buttons(message.chat.id, state)

    try:
        # Media guruhni aniqlash
        media_group_id = message.media_group_id
        if media_group_id:
            # Media guruh xabarni qayta ishlash
            if user_id not in user_media_groups:
                user_media_groups[user_id] = {}
            if media_group_id not in user_media_groups[user_id]:
                user_media_groups[user_id][media_group_id] = []
            user_media_groups[user_id][media_group_id].append(message.message_id)

            # Media guruhda dokumentlar qabul qilinmaydi
            if message.document:
                await message.answer("Media guruhida fayllar qo'llab-quvvatlanmaydi. Iltimos, fayllarni alohida yuboring.")
                return
            if message.photo:
                buf['photos'].append(message.photo[-1].file_id)
            elif message.video:
                buf['videos'].append(message.video.file_id)

            user_buffers[user_id] = buf

            # Media guruhning oxirgi xabari ekanligini tekshirish uchun qisqa kutish
            await asyncio.sleep(0.5)  # 0.5 sekund kutish, guruh xabarlari to'liq kelishi uchun
            current_group_messages = user_media_groups.get(user_id, {}).get(media_group_id, [])
            if message.message_id == max(current_group_messages):  # Eng katta message_id oxirgi xabar deb hisoblanadi
                await state.set_state(Form.action)
                keyboard, text = get_action_keyboard()  # Tugmalar va xabar
                msg = await bot.send_message(
                    chat_id=message.chat.id,
                    text=text,
                    reply_markup=keyboard
                )
                await state.update_data(last_message_id=msg.message_id)
                logging.info(f"Action tugmalari yuborildi: chat_id={message.chat.id}, message_id={msg.message_id}")
                # Media guruhni tozalash
                user_media_groups[user_id].pop(media_group_id, None)
        else:
            # Alohida kontentni qayta ishlash (dokumentlar ruxsat etiladi)
            if message.photo:
                buf['photos'].append(message.photo[-1].file_id)
            elif message.video:
                buf['videos'].append(message.video.file_id)
            elif message.document:
                buf['docs'].append(message.document.file_id)
            elif message.text:
                buf['texts'].append(message.html_text)

            user_buffers[user_id] = buf
            await state.set_state(Form.action)
            keyboard, text = get_action_keyboard()  # Tugmalar va xabar
            msg = await bot.send_message(
                chat_id=message.chat.id,
                text=text,
                reply_markup=keyboard
            )
            await state.update_data(last_message_id=msg.message_id)
            logging.info(f"Action tugmalari yuborildi: chat_id={message.chat.id}, message_id={msg.message_id}")
    except Exception as e:
        logging.error(f"Ma'lumotni qayta ishlashda xato: user_id={user_id}, xato={e}")
        await message.answer("Ma'lumotni qabul qilishda xato yuz berdi. Iltimos, qayta urinib ko'ring.")

# Form.action holatida boshqa matn kiritilganda
@dp.message(Form.action, F.text)
async def handle_action_text(message: Message, state: FSMContext):
    user_id = message.from_user.id
    buf = user_buffers.get(user_id, {"photos": [], "videos": [], "docs": [], "texts": [], "user_info": {}})
    buf['texts'].append(message.html_text)
    user_buffers[user_id] = buf
    await remove_buttons(message.chat.id, state)
    await state.set_state(Form.action)
    keyboard, text = get_action_keyboard()
    msg = await bot.send_message(
        chat_id=message.chat.id,
        text=text,
        reply_markup=keyboard
    )
    await state.update_data(last_message_id=msg.message_id)
    logging.info(f"Action tugmalari yuborildi: chat_id={message.chat.id}, message_id={msg.message_id}")
     
# Yuborish
@dp.callback_query(Form.action, F.data == "send")
async def send(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    buf = user_buffers.get(user_id)
    if not buf or not buf.get("texts"):
        keyboard, text = get_action_keyboard()
        await callback.message.answer("Iltimos, kamida bitta matn kiriting.", reply_markup=keyboard)
        await callback.answer()
        return

    try:
        # Oldingi tugmalarni va xabarni o'chirish
        await remove_buttons(callback.message.chat.id, state)

        # Matnlarni yangi qatordan birlashtirish
        combined_text = "\n".join(buf['texts'])

        # Media guruhini tayyorlash
        media = []
        for p in buf['photos']:
            media.append(types.InputMediaPhoto(media=p))
        for v in buf['videos']:
            media.append(types.InputMediaVideo(media=v))
        for d in buf['docs']:
            media.append(types.InputMediaDocument(media=d))

        # Admin uchun ma'lumotlarni yuborish
        admin_message_ids = []
        if media:
            media[0].caption = combined_text
            sent_messages = await bot.send_media_group(chat_id=ADMIN_ID, media=media)
            admin_message_ids.extend([msg.message_id for msg in sent_messages])
        else:
            sent_message = await bot.send_message(chat_id=ADMIN_ID, text=combined_text)
            admin_message_ids.append(sent_message.message_id)

        # Admin boshqaruv xabari
        user_info = buf.get('user_info', {})
        full_name = user_info.get('full_name', 'Nomalum')
        username = user_info.get('username', 'Nomalum')
        control_msg = await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"👤 <b>{full_name}</b> (@{username})",
            reply_markup=get_admin_keyboard(user_id)
        )
        admin_message_ids.append(control_msg.message_id)

        # Ma'lumotlarni saqlash
        buf['admin_message_ids'] = admin_message_ids
        user_buffers[user_id] = buf

        await callback.message.answer("Takfilingiz adminga yuborildi", reply_markup=get_main_menu())
        await state.set_state(Form.waiting)
        await callback.answer()
    except Exception as e:
        logging.error(f"Takfilni adminga yuborishda xato: user_id={user_id}, xato={e}")
        keyboard, text = get_action_keyboard()
        await callback.message.answer("Takfilni yuborishda xatolik yuz berdi. Qayta urinib ko'ring.", 
                                    reply_markup=keyboard)
        await callback.answer()

# Bekor qilish
@dp.callback_query(Form.action, F.data == "cancel")
async def cancel(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await remove_buttons(callback.message.chat.id, state)
    user_buffers.pop(user_id, None)
    if user_id in user_media_groups:
        user_media_groups.pop(user_id, None)
    await state.set_state(Form.waiting)
    await callback.message.answer("Takfil bekor qilindi. Yangi taklif yuborish uchun quyidagi tugmani bosing:", 
                                reply_markup=get_main_menu())
    await callback.answer()

# Form.action holatida boshqa matn kiritilganda
@dp.message(Form.action, F.text)
async def handle_action_text(message: Message, state: FSMContext):
    user_id = message.from_user.id
    buf = user_buffers.get(user_id, {"photos": [], "videos": [], "docs": [], "text": None})
    buf['text'] = message.html_text
    user_buffers[user_id] = buf
    await remove_buttons(message.chat.id, state)
    await state.set_state(Form.action)
    keyboard, text = get_action_keyboard()
    msg = await bot.send_message(
        chat_id=message.chat.id,
        text=text,
        reply_markup=keyboard
    )
    await state.update_data(last_message_id=msg.message_id)
    logging.info(f"Action tugmalari yuborildi: chat_id={message.chat.id}, message_id={msg.message_id}")

# Approve
@dp.callback_query(F.data.startswith("approve:"))
async def approve(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    buf = user_buffers.get(user_id)
    if not buf:
        await callback.answer("Takfil ma'lumotlari topilmadi.", show_alert=True)
        return

    try:
        # Matnlarni yangi qatordan birlashtirish
        combined_text = "\n".join(buf['texts'])

        media = []
        for p in buf['photos']:
            media.append(types.InputMediaPhoto(media=p))
        for v in buf['videos']:
            media.append(types.InputMediaVideo(media=v))
        for d in buf['docs']:
            media.append(types.InputMediaDocument(media=d))

        if media:
            media[0].caption = combined_text
            await bot.send_media_group(chat_id=CHANNEL_ID, media=media)
        else:
            await bot.send_message(chat_id=CHANNEL_ID, text=combined_text)

        await callback.message.edit_text("Takfil tasdiqlandi va kanalga joylandi.")
        user_buffers.pop(user_id, None)
        if user_id in user_media_groups:
            user_media_groups.pop(user_id, None)
        await callback.answer()
    except Exception as e:
        logging.error(f"Takfilni kanalga joylashda xato: user_id={user_id}, xato={e}")
        await callback.message.answer("Takfilni kanalga joylashda xatolik yuz berdi.")
        await callback.answer()

# Reject
@dp.callback_query(F.data.startswith("reject:"))
async def reject(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    if user_id in user_buffers:
        user_buffers.pop(user_id, None)
        if user_id in user_media_groups:
            user_media_groups.pop(user_id, None)
    await callback.message.edit_text("Takfil rad etildi.")
    await callback.answer()

# Edit
@dp.callback_query(F.data.startswith("edit:"))
async def edit(callback: types.CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[1])
    if user_id not in user_buffers:
        await callback.answer("Taklif ma'lumotlari topilmadi.", show_alert=True)
        return

    await state.set_state(Form.admin_edit)
    await state.update_data(edit_user_id=user_id, edit_msg_id=callback.message.message_id)
    combined_text = "\n".join(user_buffers[user_id]['texts']) if user_buffers[user_id]['texts'] else "Matn mavjud emas"
    await callback.message.answer(f"Joriy matn:\n{combined_text}\n\nYangi matnni kiriting:")
    await callback.answer()

@dp.message(Form.admin_edit)
async def save_edit(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("edit_user_id")
    msg_id = data.get("edit_msg_id")

    if not user_id or user_id not in user_buffers:
        await message.answer("Taklif topilmadi.")
        await state.clear()
        return

    user_buffers[user_id]['texts'] = [message.html_text]  # Yangi matn ro'yxatni almashtiradi
    try:
        # Yangi xabarni yuborish
        media = []
        for p in user_buffers[user_id]['photos']:
            media.append(types.InputMediaPhoto(media=p))
        for v in user_buffers[user_id]['videos']:
            media.append(types.InputMediaVideo(media=v))
        for d in user_buffers[user_id]['docs']:
            media.append(types.InputMediaDocument(media=d))

        admin_message_ids = user_buffers[user_id].get('admin_message_ids', [])
        # Yangi xabarni yuborish, avvalgi xabarlar saqlanadi
        combined_text = "\n".join(user_buffers[user_id]['texts'])
        if media:
            media[0].caption = combined_text
            sent_messages = await bot.send_media_group(chat_id=ADMIN_ID, media=media)
            admin_message_ids.extend([msg.message_id for msg in sent_messages])
        else:
            sent_message = await bot.send_message(chat_id=ADMIN_ID, text=combined_text)
            admin_message_ids.append(sent_message.message_id)

        # Asl foydalanuvchi ma'lumotlarini olish
        user_info = user_buffers[user_id].get('user_info', {})
        full_name = user_info.get('full_name', 'Nomalum')
        username = user_info.get('username', 'Nomalum')

        # Admin boshqaruv xabari
        control_msg = await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"👤 <b>{full_name}</b> (@{username})",
            reply_markup=get_admin_keyboard(user_id)
        )
        admin_message_ids.append(control_msg.message_id)

        user_buffers[user_id]['admin_message_ids'] = admin_message_ids
        await message.answer("Matn tahrirlandi.")
        await state.clear()
    except Exception as e:
        logging.error(f"Tahrirlangan matnni yuborishda xato: user_id={user_id}, xato={e}")
        await message.answer("Matnni tahrirlashda xatolik yuz berdi.")
        
# Run
if __name__ == '__main__':
    asyncio.run(dp.start_polling(bot))
