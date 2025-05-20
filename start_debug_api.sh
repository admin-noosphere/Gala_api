#!/bin/bash

# Script de lancement de l'API avec debugging avancé

echo "=== API Debug Avancé Gala v1 ==="
echo "Port: 6969"
echo "LiveLink: 192.168.1.14:11111"
echo ""

# Créer les dossiers de debug
mkdir -p debug_logs
mkdir -p debug_tools
chmod +x debug_tools/*.py

# Variables d'environnement
export CUDA_VISIBLE_DEVICES=0
export PYTHONPATH="${PWD}:${PYTHONPATH}"
export PYTHONUNBUFFERED=1

# Installer les dépendances si nécessaire
echo "Vérification des dépendances..."
pip install plotly matplotlib > /dev/null 2>&1

# Nettoyer les anciens logs
echo "Nettoyage des anciens logs..."
find debug_logs -name "*.log" -mtime +7 -delete

# Lancer l'API
echo ""
echo "🚀 Démarrage de l'API Debug..."
echo "📁 Logs dans: debug_logs/"
echo "🔧 Outils dans: debug_tools/"
echo ""
echo "Endpoints disponibles:"
echo "  - http://localhost:6969/health"
echo "  - http://localhost:6969/audio_to_blendshapes"
echo "  - http://localhost:6969/debug/test_pattern"
echo "  - http://localhost:6969/debug/report"
echo ""

python api_debug_advanced.py