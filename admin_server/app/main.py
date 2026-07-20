"""
Main entrypoint for the FastAPI Admin Server.
Initializes the web API for nodes, billing, and subscriptions.
Also starts background tasks like the Aiogram Telegram Bot and the scheduler.
"""

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from app.api.endpoints import nodes, billing, subs
import uvicorn
import asyncio
from app.bot.bot_main import start_bot, stop_bot
from app.services.scheduler import start_scheduler

app = FastAPI(title="VPN Admin API", description="Central Master Server API for VPN Service")

app.include_router(nodes.router, prefix="/api/nodes", tags=["nodes"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])
app.include_router(subs.router, prefix="/sub", tags=["subscriptions"])

@app.on_event("startup")
async def on_startup():
    """
    Triggered when the FastAPI application starts.
    Starts the APScheduler for periodic tasks and launches the Telegram bot as a background task.
    """
    start_scheduler()
    asyncio.create_task(start_bot())

@app.on_event("shutdown")
async def on_shutdown():
    """
    Triggered when the FastAPI application shuts down.
    Gracefully stops the Telegram bot session.
    """
    await stop_bot()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) # nosec
