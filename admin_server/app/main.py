from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from app.api.endpoints import nodes, billing, subs
import uvicorn
import asyncio
from app.bot.bot_main import start_bot, stop_bot

app = FastAPI(title="VPN Admin API")

app.include_router(nodes.router, prefix="/api/nodes", tags=["nodes"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])
app.include_router(subs.router, prefix="/sub", tags=["subscriptions"])

@app.on_event("startup")
from app.services.scheduler import start_scheduler

@app.on_event("startup")
async def on_startup():
    start_scheduler()
    asyncio.create_task(start_bot())

@app.on_event("shutdown")
async def on_shutdown():
    await stop_bot()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
