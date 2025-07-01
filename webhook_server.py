import os
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from aiogram.types import Update
from main import bot, dp  # main.py da bot va dp mavjud bo'lishi kerak

# Log
logging.basicConfig(level=logging.INFO)

# FastAPI
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Bot is working"}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        update = await request.json()
        update_obj = Update(**update)
        await dp.process_update(update_obj)
        return {"status": "ok"}
    except Exception as e:
        logging.error(f"Webhook xatosi: {e}, update: {update}")
        return JSONResponse(content={"status": "error"}, status_code=500)

@app.on_event("startup")
async def on_startup():
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        logging.error("❌ WEBHOOK_URL is not set!")
        return
    try:
        await bot.set_webhook(url=webhook_url, drop_pending_updates=True)
        logging.info(f"✅ Webhook o‘rnatildi: {webhook_url}")
    except Exception as e:
        logging.error(f"❌ Webhook o‘rnatishda xato: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
