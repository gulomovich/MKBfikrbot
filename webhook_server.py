from flask import Flask, request, Response
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import os
from main import dp, bot  # main.py dan Dispatcher va Bot import qilinadi

# Logging sozlamalari
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Flask ilovasi
app = Flask(__name__)

# Config
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_URL","https://mkbtaklifbot.onrender.com/webhook")
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 5000))

# Webhook yo'li
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = request.get_json()
    if update:
        try:
            # JSON'dan Update obyektini yaratish
            update_obj = Update(**update)
            # Asinxron vazifani sinxron kontekstda ishga tushirish
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(dp.process_update(update_obj))
            else:
                asyncio.run_coroutine_threadsafe(dp.process_update(update_obj), loop)
            return Response(status=200)
        except Exception as e:
            logging.error(f"Webhook xatosi: {e}, Update: {update}")
            return Response(status=500)
    return Response(status=400)

# Webhookni o'rnatish
async def set_webhook():
    try:
        await bot.set_webhook(url=WEBHOOK_URL, drop_pending_updates=True)
        logging.info(f"Webhook o'rnatildi: {WEBHOOK_URL}")
    except Exception as e:
        logging.error(f"Webhook o'rnatishda xato: {e}")

# Flask serverini alohida thread'da ishga tushirish
def run_flask():
    from threading import Thread
    Thread(target=app.run, kwargs={'host': WEBAPP_HOST, 'port': WEBAPP_PORT}).start()

if __name__ == "__main__":
    # Webhookni o'rnatish
    loop = asyncio.get_event_loop()
    loop.run_until_complete(set_webhook())
    # Flask serverini ishga tushirish
    run_flask()
