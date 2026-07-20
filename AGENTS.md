# 🤖 Guidelines for AI Agents

This repository contains a modern VPN service architecture divided into two main components: an **Admin Server** (Master) and **Node Servers** (Slaves).

## 📁 Repository Structure

- `admin_server/` - The central management server.
  - Built with FastAPI (API), Aiogram 3 (Telegram Bot), SQLAlchemy (PostgreSQL ORM), and Alembic (migrations).
  - Handles billing, user management, and subscription generation.
- `node_server/` - The VPN traffic node.
  - Contains Xray-core (for VLESS + Reality VPN protocols).
  - Runs a Python reporting agent (`node_server/agent/main.py`) that syncs user configurations and reports traffic usage back to the `admin_server` every 10 minutes.
- `install.sh` - The unified deployment script. Dynamically generates `docker-compose.yml` for different installation modes (Master+Node, Master only, Node only).

## 🧠 Key Logic & Billing

- **Billing Model:** Pay-as-you-go. 1 GB = 1 RUB.
- Traffic is tracked on the `node_server` via Xray API (`statsquery`).
- The `node_server/agent/main.py` fetches traffic usage, aggregates it, and sends it to the `admin_server` via the `/api/nodes/stats` endpoint.
- If a user's balance drops below -50 RUB, they are blocked (`is_active = False`).
- **Routing (Split-tunneling):** The admin server generates Sing-box JSON or VLESS links. Users can toggle "direct RU" routing, which generates rules to bypass the VPN for Russian domains.

## 🛠️ Instructions for Modifying Code

1. **Database Changes:** If you modify `admin_server/app/db/models.py`, you **must** generate a new Alembic migration using `alembic revision --autogenerate -m "description"` inside the `admin_server` container, and then run `alembic upgrade head`. (Or write the migration script manually if you cannot run the container).
2. **Environment Variables:** The system heavily relies on `.env` variables (e.g., `ADMIN_API_KEY`, `BOT_TOKEN`, `REALITY_PRIVATE_KEY`). Ensure these are mocked or handled gracefully during tests.
3. **API Security:** Endpoints under `/api/nodes/` are protected by `X-Admin-API-Key`.
4. **Xray Config:** The `node_server/agent/main.py` directly modifies `/app/xray/config.json` to add/remove users and apply `REALITY` keys, then restarts Xray (`pkill xray`).

## 🧪 Testing

- When writing tests, mock the external Telegram API and Xray binary calls.
- Use `pytest` for testing the FastAPI application.

*Note: Always verify your changes using `read_file` or running relevant scripts/linters.*
