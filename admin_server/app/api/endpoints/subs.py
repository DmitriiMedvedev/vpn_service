from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import base64
import json
import os

from app.db.database import get_session
from app.db.models import User, Node

router = APIRouter()

def generate_vless_link(uuid: str, ip: str, port: int, index: int = 1):
    pbk = os.getenv("REALITY_PUBLIC_KEY", "YOUR_PUBLIC_KEY")
    sid = os.getenv("REALITY_SHORT_ID", "YOUR_SHORT_ID")
    sni = "www.microsoft.com"
    return f"vless://{uuid}@{ip}:{port}?type=tcp&security=reality&pbk={pbk}&sni={sni}&sid={sid}&fp=chrome&flow=xtls-rprx-vision#VPN-Node-{index}"

def generate_singbox_profile(uuid: str, nodes: list, split_tunneling: bool):
    # Base Sing-box configuration
    config = {
        "log": {"level": "info"},
        "dns": {
            "servers": [{"tag": "google", "address": "8.8.8.8"}],
            "rules": [{"outbound": "any", "server": "google"}]
        },
        "inbounds": [{"type": "tun", "tag": "tun-in", "inet4_address": "172.19.0.1/30", "auto_route": True}],
        "outbounds": [],
        "route": {"rules": []}
    }

    # Generate node tags
    node_tags = [f"node-{i}" for i in range(len(nodes))]

    # Add a selector outbound as the very first outbound
    if node_tags:
        config["outbounds"].append({
            "type": "selector",
            "tag": "select",
            "outbounds": node_tags,
            "default": node_tags[0]
        })

    # Add nodes as outbounds
    for i, node in enumerate(nodes):
        config["outbounds"].append({
            "type": "vless",
            "tag": f"node-{i}",
            "server": node.ip,
            "server_port": node.port,
            "uuid": uuid,
            "network": "tcp",
            "flow": "xtls-rprx-vision",
            "tls": {
                "enabled": True,
                "server_name": "www.microsoft.com",
                "utls": {"enabled": True, "fingerprint": "chrome"},
                "reality": {
                    "enabled": True,
                    "public_key": os.getenv("REALITY_PUBLIC_KEY", "YOUR_PUBLIC_KEY"),
                    "short_id": os.getenv("REALITY_SHORT_ID", "YOUR_SHORT_ID")
                }
            }
        })

    config["outbounds"].append({"type": "direct", "tag": "direct"})

    if split_tunneling:
        # Route RU domains to direct
        config["route"]["rules"].append({
            "domain_suffix": [".ru", ".su", ".рф"],
            "outbound": "direct"
        })
        # Note: True geoip routing would require geoip.db on client
        config["route"]["rules"].append({
            "geoip": ["ru"],
            "outbound": "direct"
        })

    return config

@router.get("/{uuid}", response_class=PlainTextResponse)
async def get_subscription(uuid: str, request: Request, db: AsyncSession = Depends(get_session)):
    stmt = select(User).where(User.uuid == uuid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_active or user.is_blocked_by_admin:
        return ""

    stmt_nodes = select(Node).where(Node.status == "active")
    result_nodes = await db.execute(stmt_nodes)
    nodes = result_nodes.scalars().all()

    user_agent = request.headers.get("User-Agent", "").lower()

    # If the client supports Sing-box JSON (like Happ or v2rayN configured for it)
    if "sing-box" in user_agent or "happ" in user_agent:
        profile = generate_singbox_profile(user.uuid, nodes, user.split_tunneling)
        return json.dumps(profile, indent=2)
    else:
        # Fallback to basic vless links (which rely on the client's own routing UI)
        links = [generate_vless_link(user.uuid, node.ip, node.port, index=i+1) for i, node in enumerate(nodes)]
        sub_data = "\n".join(links)
        return base64.b64encode(sub_data.encode('utf-8')).decode('utf-8')
