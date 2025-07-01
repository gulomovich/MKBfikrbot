from flask import Flask, request, Response
import asyncio
import logging
from aiogram import Bot, Dispatcher
from main import dp, bot  # Bu yerda bot va dp faqat yaratilgan bo'lishi kerak
import os

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Flask app
app = Flask(__name__)

# Config
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://mkbtaklifbot.onrender.com/webhook")
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 5000))

# Webhook route (SYNC!)
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = request.get_json()
    if update:
        try:
            asyncio.create_task(dp.feed_raw_update(bot=bot, update=update))
            logging.info("✅ Webhook update received and scheduled")
            return Response(status=200)
        except Exception as e:
            logging.error(f"❌ Webhook error: {e}")
            return Response(status=500)
    logging.warning("⚠️ No valid update received")
    return Response(status=400)

# Health check (for Render)
@app.route("/", methods=["GET", "HEAD"])
def index():
    return "Bot is running", 200

# Webhook o‘rnatish
async def set_webhook():
    try:
        await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
        logging.info(f"✅ Webhook o'rnatildi: {WEBHOOK_URL}")
    except Exception as e:
        logging.error(f"❌ Webhook o'rnatishda xato: {e}")

if __name__ == "__main__":
    # Faqat lokalda test uchun
    asyncio.run(set_webhook())
    app.run(host=WEBAPP_HOST, port=WEBAPP_PORT)
