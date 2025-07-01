from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import os
import logging

# Logging sozlamalari
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# FastAPI ilovasi
app = FastAPI()

# Bot va Dispatcher sozlamalari
bot = Bot(token=os.getenv("BOT_TOKEN", "7795753797:AAF97ku5-weFRMISUMfAYI1YfxVx5wOz7u0"), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Webhook yo'li
@app.post("/webhook")
async def webhook(request: Request):
    try:
        update = await request.json()
        update_obj = Update(**update)
        await dp.process_update(update_obj)
        return {"status": "ok"}
    except Exception as e:
        logging.error(f"Webhook xatosi: {e}, Update: {update}")
        return {"status": "error"}, 500

# Ilova ishga tushganda webhookni o'rnatish
@app.on_event("startup")
async def on_startup():
    webhook_url = os.getenv("WEBHOOK_URL","https://mkbtaklifbot.onrender.com/webhook")
    try:
        await bot.set_webhook(url=webhook_url, drop_pending_updates=True)
        logging.info(f"Webhook o'rnatildi: {webhook_url}")
    except Exception as e:
        logging.error(f"Webhook o'rnatishda xato: {e}")

# main.py dan handlerlarni import qilish (agar kerak bo'lsa)
from main import dp  # Agar handlerlar main.py da bo'lsa

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
