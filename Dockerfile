# -----------------------------
# 1. Image de base
# -----------------------------
FROM python:3.10-slim

# -----------------------------
# 2. Variables d’environnement
# -----------------------------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# -----------------------------
# 3. Installation des dépendances système
# -----------------------------
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------
# 4. Création du dossier app
# -----------------------------
WORKDIR /app

# -----------------------------
# 5. Copie des fichiers requirements
# -----------------------------
COPY requirements.txt .

# -----------------------------
# 6. Installation des dépendances Python
# -----------------------------
RUN pip install --no-cache-dir -r requirements.txt

ENV MONGO_URL=mongodb://host.docker.internal:27017/

# -----------------------------
# 7. Copie du code de l’application
# -----------------------------
COPY . .

# -----------------------------
# 8. Exposition du port Flask
# -----------------------------
EXPOSE 5000

# -----------------------------
# 9. Commande de lancement
# -----------------------------
CMD ["python", "main.py"]
