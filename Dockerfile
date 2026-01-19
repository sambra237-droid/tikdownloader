# Image Python officielle
FROM python:3.11-slim

# Mettre à jour et installer dépendances système
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /main

# Copier les fichiers nécessaires
COPY requirements.txt .
COPY main.py .  # assure-toi que ton fichier s'appelle app.py

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Exposer le port utilisé par Railway
EXPOSE 8080

# Lancer Flask via gunicorn pour production
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
