FROM python:3.11-slim

# Dépendances système
RUN apt-get update && apt-get install -y \
    wget unzip curl gnupg ca-certificates fonts-liberation \
    libappindicator3-1 libasound2 libatk-bridge2.0-0 libatk1.0-0 \
    libc6 libcairo2 libcups2 libdbus-1-3 libexpat1 libfontconfig1 \
    libgbm1 libgcc1 libglib2.0-0 libgtk-3-0 libnspr4 libnss3 \
    libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 \
    libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 \
    libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 \
    libxtst6 lsb-release xdg-utils --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Installer Chrome version 137
RUN mkdir -p /opt/chrome && \
    wget -q https://storage.googleapis.com/chrome-for-testing-public/137.0.7151.70/linux64/chrome-linux64.zip && \
    unzip chrome-linux64.zip -d /opt/chrome && \
    rm chrome-linux64.zip && \
    ln -s /opt/chrome/chrome-linux64/chrome /usr/bin/google-chrome

# Installer ChromeDriver version 137
RUN mkdir -p /opt/chromedriver && \
    wget -q https://storage.googleapis.com/chrome-for-testing-public/137.0.7151.70/linux64/chromedriver-linux64.zip && \
    unzip chromedriver-linux64.zip -d /opt/chromedriver && \
    mv /opt/chromedriver/chromedriver-linux64/chromedriver /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver && \
    rm chromedriver-linux64.zip

# Installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY . /app
WORKDIR /app

# Port requis pour Render
ENV PORT=10000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
