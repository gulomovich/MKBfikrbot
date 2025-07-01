from flask import Flask, request, Response
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from main import dp, bot
import os

# Logging sozlamalari
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Flask ilovasi
app = Flask(__name__)

# Config
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://mkbtaklifbot.onrender.com/webhook")
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 5000))  # Default to 5000 for Render

# Webhook yo'li
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    logging.info(f"Received request at /webhook: method={request.method}, data={request.get_json(silent=True)}")
    update = request.get_json()
    if update:
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(dp.feed_raw_update(bot=bot, update=update))
            logging.info("Webhook update processed successfully")
            return Response(status=200)
        except Exception as e:
            logging.error(f"Webhook xatosi: {e}")
            return Response(status=500)
    logging.warning("No valid JSON data received in webhook request")
    return Response(status=400)

# Health check endpoint for Render
@app.route("/", methods=["GET", "HEAD"])
def health_check():
    logging.info(f"Health check requested: method={request.method}")
    return Response(status=200)

# Webhook o'rnatish
async def set_webhook():
    try:
        if not WEBHOOK_URL:
            logging.error("WEBHOOK_URL is not set in environment variables")
            return
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url != WEBHOOK_URL:
            await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True, allowed_updates=["message", "callback_query"])
            logging.info(f"Webhook o'rnatildi: {WEBHOOK_URL}")
        else:
            logging.info(f"Webhook already set to: {WEBHOOK_URL}")
    except Exception as e:
        logging.error(f"Webhook o'rnatishda xato: {e}")

# Gunicorn ishga tushganda webhook o'rnatish
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(set_webhook())
    app.run(host=WEBAPP_HOST, port=WEBAPP_PORT)
else:
    # Gunicorn orqali ishlaganda webhook o'rnatish
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(set_webhook())
