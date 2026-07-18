from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import base64
import json

from app.db.database import get_session
from app.db.models import User, Node

router = APIRouter()

def generate_vless_link(uuid: str, ip: str, port: int, split_tunneling: bool):
    # Base VLESS string (Reality)
    # Using sample values for SNI, pbk, etc. In production, these come from Node config.
    pbk = "YOUR_PUBLIC_KEY" # Placeholder
    sid = "YOUR_SHORT_ID"   # Placeholder
    sni = "www.microsoft.com"

    # Simple vless URL
    url = f"vless://{uuid}@{ip}:{port}?type=tcp&security=reality&pbk={pbk}&sni={sni}&sid={sid}&fp=chrome#VPN-Node"

    # To support Happ / v2rayN with split tunneling properly, we could wrap it in a Base64 subscription
    # Happ usually parses the raw vless:// links or Clash/Sing-box formats.
    # For now, we provide the raw link. The client handles its own routing rules in Happ if they use vless://
    return url

@router.get("/{uuid}", response_class=PlainTextResponse)
async def get_subscription(uuid: str, db: AsyncSession = Depends(get_session)):
    stmt = select(User).where(User.uuid == uuid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_active or user.is_blocked_by_admin:
        return "" # Empty sub for blocked users

    stmt_nodes = select(Node).where(Node.status == "active")
    result_nodes = await db.execute(stmt_nodes)
    nodes = result_nodes.scalars().all()

    links = []
    for node in nodes:
        link = generate_vless_link(user.uuid, node.ip, node.port, user.split_tunneling)
        links.append(link)

    sub_data = "\n".join(links)
    return base64.b64encode(sub_data.encode('utf-8')).decode('utf-8')
