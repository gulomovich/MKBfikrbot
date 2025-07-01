# webhook.py
import logging
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from bot import bot, dp  # Sizning botingiz shu faylda (bot.py)

app = FastAPI()

# Webhook endpoint
@app.post("/")
async def webhook_handler(request: Request):
    try:
        data = await request.json()
        update = Update.model_validate(data)
        await dp.feed_update(bot, update)
    except Exception as e:
        logging.error(f"Webhook xatoligi: {e}")
    return {"ok": True}
