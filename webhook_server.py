from flask import Flask, request, Response
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from main import dp, bot
import os
import time
import aiohttp

# Logging sozlamalari
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Flask ilovasi
app = Flask(__name__)

# Config
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_URL","https://mkbtaklifbot.onrender.com/webhook")
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

# Handle POST to / for debugging
@app.route("/", methods=["POST"])
def root_post():
    logging.warning(f"Received POST request at /: data={request.get_json(silent=True)}")
    return Response("POST requests should be sent to /webhook", status=405)

# Webhook o'rnatish with retries and session management
async def set_webhook():
    max_retries = 3
    retry_delay = 5  # seconds
    async with aiohttp.ClientSession() as session:
        for attempt in range(max_retries):
            try:
                if not WEBHOOK_URL:
                    logging.error("WEBHOOK_URL is not set in environment variables")
                    raise ValueError("WEBHOOK_URL is not set")
                if not os.getenv("BOT_TOKEN"):
                    logging.error("BOT_TOKEN is not set in environment variables")
                    raise ValueError("BOT_TOKEN is not set")
                webhook_info = await bot.get_webhook_info(session=session)
                logging.info(f"Current webhook info: {webhook_info}")
                if webhook_info.url != WEBHOOK_URL:
                    await bot.set_webhook(
                        WEBHOOK_URL,
                        drop_pending_updates=True,
                        allowed_updates=["message", "callback_query"],
                        session=session
                    )
                    logging.info(f"Webhook o'rnatildi: {WEBHOOK_URL}")
                    return
                else:
                    logging.info(f"Webhook already set to: {WEBHOOK_URL}")
                    return
            except Exception as e:
                logging.error(f"Webhook o'rnatishda xato (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logging.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logging.error("Max retries reached. Webhook setup failed.")
                    raise

# Gunicorn ishga tushganda webhook o'rnatish
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(set_webhook())
    app.run(host=WEBAPP_HOST, port=WEBAPP_PORT)
else:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(set_webhook())
