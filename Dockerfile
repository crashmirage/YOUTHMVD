# On part d'une image officielle Python
FROM python:3.11-slim

# Installer les dépendances nécessaires pour Chrome et Selenium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg2 \
    curl \
    unzip \
    fonts-liberation \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libasound2 \
    libxrandr2 \
    libgbm-dev \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Installer Chromium (version stable)
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
 && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list \
 && apt-get update && apt-get install -y google-chrome-stable --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*

# Installer ChromeDriver (compatible avec la version Chrome stable)
RUN CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+') \
 && CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}") \
 && wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" \
 && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
 && rm /tmp/chromedriver.zip \
 && chmod +x /usr/local/bin/chromedriver

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Copier les fichiers requirements.txt et installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le code dans /app
COPY . .

# Exposer le port utilisé par FastAPI
EXPOSE 8000

# Commande pour lancer l'application avec Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
