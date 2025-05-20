#!/bin/bash

# Script de lancement en mode performance (sans logging)

echo "=== API Gala v1 - Mode Performance ==="
echo "Logging désactivé pour éviter les saccades"
echo ""

# Variables d'environnement pour le mode performance
export PERFORMANCE_MODE=ON
export DEBUG_MODE=OFF
export CUDA_VISIBLE_DEVICES=0
export PYTHONPATH="${PWD}:${PYTHONPATH}"
export PYTHONUNBUFFERED=1

# Optimisations Python
export PYTHONOPTIMIZE=1

echo "Configuration:"
echo "  - Performance Mode: ON"
echo "  - Debug Mode: OFF"
echo "  - Port: 6969"
echo "  - LiveLink: 192.168.1.14:11111"
echo ""

python api_optimized.py