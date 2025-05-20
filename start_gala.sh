#!/bin/bash
"""
Script de démarrage pour Gala v1
Lance l'API unifiée et l'application principale
"""

echo "=== Démarrage de Gala v1 ==="

# Vérifier les dépendances
echo "Vérification des dépendances..."
pip install -r requirements.txt

# Charger les variables d'environnement
if [ -f .env ]; then
    echo "Chargement des variables d'environnement..."
    export $(cat .env | xargs)
else
    echo "Fichier .env non trouvé. Copiez .env.example vers .env et configurez vos clés API."
    exit 1
fi

# Lancer l'API unifiée en arrière-plan
echo "Démarrage de l'API unifiée sur le port 6969..."
python api_client.py &
API_PID=$!

# Attendre que l'API soit prête
echo "Attente de l'API..."
sleep 5

# Vérifier que l'API répond
if curl -s http://localhost:6969/health > /dev/null; then
    echo "API prête!"
else
    echo "L'API ne répond pas. Vérifiez les logs."
    kill $API_PID
    exit 1
fi

# Lancer l'application principale
echo "Démarrage de Gala..."
python main.py

# Nettoyage
echo "Arrêt de l'API..."
kill $API_PID

echo "=== Gala v1 arrêté ==="