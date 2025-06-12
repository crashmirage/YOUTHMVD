FROM python:3.11-slim

# Installer les dépendances système et Chrome stable
RUN apt-get update && \
    apt-get install -y wget gnupg curl unzip \
                       fonts-liberation libnss3 libx11-xcb1 libxcomposite1 \
                       libxcursor1 libxdamage1 libxrandr2 libgbm1 libasound2 \
                       libatk1.0-0 libatk-bridge2.0-0 libcups2 libxss1 libgtk-3-0 \
                       libpangocairo-1.0-0 libxshmfence1 \
                       ca-certificates && \
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Définir répertoire de travail
WORKDIR /app

# Copier et installer les dépendances Python
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY . .

# Définir le port d’écoute
EXPOSE 8000

# Lancer FastAPI
CMD ["uvicorn", "main_MVD_ARIA:app", "--host", "0.0.0.0", "--port", "8000"]
