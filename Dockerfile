# Étape 1 : base avec Chrome et Node.js
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Installer Google Chrome stable (utile pour undetected-chromedriver)
RUN apt-get update && \
    apt-get install -y wget gnupg curl unzip && \
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Fix permissions
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances Python
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copier le reste du code
COPY . .

# Exposer le port
EXPOSE 8000

# Lancer l’app FastAPI avec Uvicorn
CMD ["uvicorn", "main_MVD_ARIA:app", "--host", "0.0.0.0", "--port", "8000"]
