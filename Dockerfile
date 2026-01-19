# Image Python officielle
FROM python:3.11-slim

# Installer dépendances système
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Répertoire de travail
WORKDIR /main

# Copier fichiers
COPY requirements.txt .
COPY main.py .   # main.py doit être au même niveau que Dockerfile

# Installer dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Exposer le port
EXPOSE 8080

# Lancer Flask via Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "main:app"]




