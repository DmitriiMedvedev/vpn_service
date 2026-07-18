FROM python:3.11-slim

# Install Xray
RUN apt-get update && apt-get install -y wget unzip \
    && wget -O xray.zip https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip \
    && unzip xray.zip -d /usr/local/bin \
    && rm xray.zip \
    && chmod +x /usr/local/bin/xray \
    && apt-get remove -y wget unzip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Copy Xray config to standard location or keep in app
# We'll use /app/xray/config.json in our startup script

# Create a startup script that runs both Xray and the Python Agent
RUN echo '#!/bin/bash\n\
while true; do xray run -c /app/xray/config.json & XRAY_PID=$!; wait $XRAY_PID; sleep 1; done xray run -c /app/xray/config.json &\n\
python /app/agent/main.py\n\
' > /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]
