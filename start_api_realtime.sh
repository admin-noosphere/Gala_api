#!/bin/bash

# Script de lancement de l'API Real-Time Clone

echo "=== Lancement de l'API Real-Time Clone Gala v1 ==="
echo "Port API: 6969"
echo "LiveLink: 192.168.1.14:11111"

# Activer l'environnement virtuel si disponible
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Variables d'environnement
export CUDA_VISIBLE_DEVICES=0
export PYTHONPATH="${PWD}:${PYTHONPATH}"

# Copier la config si nécessaire
NEUROSYNC_PATH="/home/gieidi-prime/Agents/NeuroSync_Local_API/neurosync_v3_all copy/NeuroSync_Real-Time_API"
if [ -f "$NEUROSYNC_PATH/models/neurosync/config.py" ] && [ ! -f "config.py" ]; then
    echo "Copie du fichier config.py..."
    cp "$NEUROSYNC_PATH/models/neurosync/config.py" .
fi

# Lancer l'API
echo "Démarrage de l'API Real-Time Clone..."
python api_realtime_clone.py