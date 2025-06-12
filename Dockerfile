# Image de base avec Chromium déjà préinstallé
FROM ghcr.io/puppeteer/puppeteer:latest

# Installer Python 3 + pip + utilitaires système nécessaires
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /app

# Copier les dépendances et installer les paquets Python
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copier tout le code source dans le conteneur
COPY . .

# Exposer le port d'écoute de FastAPI
EXPOSE 8000

# Commande de démarrage de l'application
CMD ["uvicorn", "main_MVD_ARIA:app", "--host", "0.0.0.0", "--port", "8000"]
