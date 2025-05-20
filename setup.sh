#!/bin/bash

# Script de configuration pour Gala v1

echo "Configuration de Gala v1..."

# Créer les dossiers nécessaires
mkdir -p models/neurosync/model

# Copier ou lier le modèle NeuroSync
MODEL_SOURCE="/home/gieidi-prime/Agents/NeuroSync_Local_API/neurosync_v3_all copy/NeuroSync_Real-Time_API/models/neurosync"
MODEL_DEST="models/neurosync"

if [ -d "$MODEL_SOURCE" ]; then
    echo "Copie du modèle NeuroSync..."
    cp -r "$MODEL_SOURCE"/* "$MODEL_DEST/"
    echo "Modèle copié avec succès"
else
    echo "ERREUR: Modèle source non trouvé : $MODEL_SOURCE"
    exit 1
fi

echo "Installation des dépendances Python..."
pip install -r requirements.txt

echo "Configuration terminée !"
echo "Pour lancer l'API : python api_client.py"
