# set_webhook.py
import asyncio
from bot import bot

WEBHOOK_URL = "https://mkbtaklifbot.onrender.com/webhook"  # Render domainingizni yozing

async def main():
    await bot.set_webhook(WEBHOOK_URL)
    print("Webhook muvaffaqiyatli o‘rnatildi:", WEBHOOK_URL)

if __name__ == "__main__":
    asyncio.run(main())
