#!/bin/bash
# Fix timeout requests
sed -i 's/requests.post(f"{ADMIN_API_URL}\/api\/nodes\/stats", json=payload, headers=HEADERS)/requests.post(f"{ADMIN_API_URL}\/api\/nodes\/stats", json=payload, headers=HEADERS, timeout=10)/' node_server/agent/main.py
sed -i 's/requests.get(f"{ADMIN_API_URL}\/api\/nodes\/sync", headers=HEADERS)/requests.get(f"{ADMIN_API_URL}\/api\/nodes\/sync", headers=HEADERS, timeout=10)/' node_server/agent/main.py

# Ignore bare excepts in scheduler (logging error instead of pass)
sed -i 's/except:/except Exception as e:/g' admin_server/app/services/scheduler.py
sed -i 's/pass/print(f"Error sending message: {e}")/g' admin_server/app/services/scheduler.py

# Fix mock_token warning by ignoring it (it's a deliberate placeholder)
sed -i 's/BOT_TOKEN != "mock_token":/BOT_TOKEN != "mock_token":  # nosec/g' admin_server/app/bot/bot_main.py
