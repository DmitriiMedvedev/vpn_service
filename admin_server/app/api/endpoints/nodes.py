from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List, Dict
import os

from app.db.database import get_session
from app.db.models import User

router = APIRouter()

API_KEY_HEADER = APIKeyHeader(name="X-Admin-API-Key")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "default_secret_key")

def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    if api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key

class TrafficStat(BaseModel):
    uuid: str
    downloaded_bytes: int
    uploaded_bytes: int

class TrafficReport(BaseModel):
    node_ip: str
    stats: List[TrafficStat]

@router.post("/stats")
async def report_traffic(report: TrafficReport, db: AsyncSession = Depends(get_session), _: str = Depends(verify_api_key)):
    # Billing logic: 20 GB = 20 RUB -> 1 GB = 1 RUB -> 1 Byte = 1 / (1024^3) RUB
    COST_PER_BYTE = 1.0 / (1024 * 1024 * 1024)

    for stat in report.stats:
        total_bytes = stat.downloaded_bytes + stat.uploaded_bytes
        if total_bytes > 0:
            cost = total_bytes * COST_PER_BYTE

            # Reduce user balance
            stmt = select(User).where(User.uuid == stat.uuid)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                user.balance -= cost

                # Check for overdraft block
                if user.balance < -50.0 and user.is_active:
                    user.is_active = False

    await db.commit()
    return {"status": "ok"}

@router.get("/sync")
async def sync_users(db: AsyncSession = Depends(get_session), _: str = Depends(verify_api_key)):
    # Return all active users so nodes can update their Xray configs
    stmt = select(User.uuid).where(User.is_active == True).where(User.is_blocked_by_admin == False)
    result = await db.execute(stmt)
    active_uuids = [row[0] for row in result.all()]

    return {"active_uuids": active_uuids}
