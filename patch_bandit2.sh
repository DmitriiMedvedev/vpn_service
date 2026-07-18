#!/bin/bash
# Check why admin_server/app/main.py has syntax error
sed -i 's/except:/except Exception as e:/g' admin_server/app/bot/handlers/user.py
sed -i 's/pass/print(f"Error handling ref: {e}")/g' admin_server/app/bot/handlers/user.py
