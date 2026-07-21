FROM python:3.11-slim

# Install Xray and procps (for pkill)
ENV XRAY_VERSION="v1.8.24"
ENV XRAY_SHA256="47a860787e823474a358d6bca536547df6dd08b69c6de482ea92a9e7e8f8969c"

RUN apt-get update && apt-get install -y wget unzip procps coreutils \
    && wget -O xray.zip https://github.com/XTLS/Xray-core/releases/download/${XRAY_VERSION}/Xray-linux-64.zip \
    && echo "${XRAY_SHA256}  xray.zip" | sha256sum -c - \
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

# Create a startup script that runs both Xray and the Python Agent
RUN echo '#!/bin/bash\n\
(while true; do /usr/local/bin/xray run -c /app/xray/config.json; sleep 1; done) &\n\
python /app/agent/main.py\n\
' > /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]
