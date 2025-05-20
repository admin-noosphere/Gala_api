#!/bin/bash

# Script de lancement en mode debug (avec logging complet)

echo "=== API Gala v1 - Mode Debug ==="
echo "Logging complet activé (peut causer des saccades)"
echo ""

# Variables d'environnement pour le mode debug
export PERFORMANCE_MODE=OFF
export DEBUG_MODE=ON
export CUDA_VISIBLE_DEVICES=0
export PYTHONPATH="${PWD}:${PYTHONPATH}"
export PYTHONUNBUFFERED=1

# Créer le dossier de logs
mkdir -p debug_logs

echo "Configuration:"
echo "  - Performance Mode: OFF"
echo "  - Debug Mode: ON"
echo "  - Port: 6969"
echo "  - LiveLink: 192.168.1.14:11111"
echo "  - Logs: debug_logs/"
echo ""

python api_optimized.py 2>&1 | tee debug_logs/api_$(date +%Y%m%d_%H%M%S).log