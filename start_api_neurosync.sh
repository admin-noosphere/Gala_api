#!/bin/bash

# Script de lancement de l'API NeuroSync avec LiveLink

echo "=== Lancement de l'API NeuroSync Gala v1 ==="
echo "Port API: 6969"
echo "LiveLink: 192.168.1.14:11111"

# Activer l'environnement virtuel si disponible
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Variables d'environnement
export CUDA_VISIBLE_DEVICES=0
export PYTHONPATH="${PWD}:${PYTHONPATH}"

# Lancer l'API
echo "Démarrage de l'API..."
python api_client_neurosync.py

# Si l'API principale échoue, essayer le fallback
if [ $? -ne 0 ]; then
    echo "Erreur avec api_client_neurosync.py, essai de l'API originale..."
    python api_client.py
fi