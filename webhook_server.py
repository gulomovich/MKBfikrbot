from flask import Flask, request, Response
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from main import dp, bot  # main.py dan Dispatcher va Bot import qilinadi
import os

# Logging sozlamalari
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Flask ilovasi
app = Flask(__name__)

# Config
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_URL","https://mkbtaklifbot.onrender.com/")

# Webhook yo'li
@app.route(WEBHOOK_PATH, methods=["POST"])
async def webhook():
    update = request.get_json()
    if update:
        try:
            # Aiogram Dispatcher orqali yangilanishni qayta ishlash
            await dp.feed_raw_update(bot=bot, update=update)
            return Response(status=200)
        except Exception as e:
            logging.error(f"Webhook xatosi: {e}")
            return Response(status=500)
    return Response(status=400)

# Flask ilovasini ishga tushirish
async def set_webhook():
    try:
        await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
        logging.info(f"Webhook o'rnatildi: {WEBHOOK_URL}")
    except Exception as e:
        logging.error(f"Webhook o'rnatishda xato: {e}")

if __name__ == "__main__":
    # Botni webhook rejimida ishga tushirish
    asyncio.run(set_webhook())
    app.run(host='0.0.0.0', port=5000)
