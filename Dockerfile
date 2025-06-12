FROM ghcr.io/puppeteer/puppeteer:latest

# Installer Python
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Installer dépendances Python
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copier le code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main_MVD_ARIA:app", "--host", "0.0.0.0", "--port", "8000"]


# Installer dépendances Python
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copier code
COPY . .

EXPOSE 8000
CMD ["uvicorn", "main_MVD_ARIA:app", "--host", "0.0.0.0", "--port", "8000"]
