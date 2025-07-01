from flask import Flask, request, Response
import asyncio
import logging
import os
from main import dp, bot  # main.py da token va dispatcher bor

# Logging
logging.basicConfig(level=logging.INFO)

# Flask app
app = Flask(__name__)

# Config
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://mkbtaklifbot.onrender.com/webhook")
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 5000))

# Webhook route
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = request.get_json()
    if update:
        try:
            asyncio.create_task(dp.feed_raw_update(bot=bot, update=update))
            return Response(status=200)
        except Exception as e:
            logging.error(f"Webhook xatosi: {e}")
            return Response(status=500)
    return Response(status=400)

# Webhook setup
async def set_webhook():
    try:
        await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
        logging.info(f"Webhook o'rnatildi: {WEBHOOK_URL}")
    except Exception as e:
        logging.error(f"Webhook o'rnatishda xato: {e}")

if __name__ == "__main__":
    asyncio.run(set_webhook())
    app.run(host=WEBAPP_HOST, port=WEBAPP_PORT)
