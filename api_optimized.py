#!/usr/bin/env python3
"""
API optimisée avec logging désactivable pour performance temps réel
"""

import os
import sys
import json
import time
import socket
import logging
import warnings
warnings.filterwarnings("ignore")

from flask import Flask, request, jsonify
from datetime import datetime

# Configuration GPU
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

import torch
import numpy as np

# Paths
neurosync_path = "/home/gieidi-prime/Agents/NeuroSync_Local_API/neurosync_v3_all copy/NeuroSync_Real-Time_API"
sys.path.insert(0, neurosync_path)

# Imports NeuroSync
from models.neurosync.config import config
from models.neurosync.generate_face_shapes import generate_facial_data_from_bytes
from models.neurosync.model.model import load_model

# Module LiveLink
sys.path.append('/home/gieidi-prime/Agents/Claude/Gala_v1')
from modules.pylivelinkface import PyLiveLinkFace, FaceBlendShape

# Configuration
LIVELINK_IP = "192.168.1.14"
LIVELINK_PORT = 11111
API_PORT = 6969

# Contrôle du logging
DEBUG_MODE = os.environ.get('DEBUG_MODE', 'OFF').upper() == 'ON'
PERFORMANCE_MODE = os.environ.get('PERFORMANCE_MODE', 'ON').upper() == 'ON'

# Configuration du logging selon le mode
if DEBUG_MODE:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s'
    )
else:
    # Mode performance : logging minimal
    logging.basicConfig(
        level=logging.WARNING,
        format='%(levelname)s | %(message)s'
    )

logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Variables globales
blendshape_model = None
py_face = None
socket_connection = None
frame_counter = 0

# Cache pour éviter les allocations répétées
cached_zero_blendshapes = [0.0] * 52

def load_neurosync_model():
    """Charge le modèle NeuroSync"""
    global blendshape_model
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    if not PERFORMANCE_MODE:
        logger.info(f"Chargement du modèle NeuroSync sur {device}")
    
    model_path = os.path.join(neurosync_path, 'models/neurosync/model/model.pth')
    blendshape_model = load_model(model_path, config, device)
    
    if not PERFORMANCE_MODE:
        logger.info("Modèle NeuroSync chargé")
    
    return blendshape_model

def init_livelink():
    """Initialise la connexion LiveLink"""
    global py_face, socket_connection
    
    if not PERFORMANCE_MODE:
        logger.info(f"Initialisation LiveLink vers {LIVELINK_IP}:{LIVELINK_PORT}")
    
    py_face = PyLiveLinkFace(name="GalaFace", fps=60)
    socket_connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_connection.connect((LIVELINK_IP, LIVELINK_PORT))
    
    # Test de connexion silencieux
    try:
        py_face.reset()
        test_data = py_face.encode()
        socket_connection.sendall(test_data)
        if not PERFORMANCE_MODE:
            logger.info("LiveLink connecté")
    except Exception as e:
        logger.error(f"Erreur LiveLink: {e}")

def send_to_livelink_optimized(blendshapes):
    """Version optimisée de l'envoi LiveLink"""
    global py_face, socket_connection
    
    if not py_face or not socket_connection:
        return
    
    try:
        # Reset efficace
        py_face._blend_shapes = cached_zero_blendshapes.copy()
        
        # Appliquer uniquement les valeurs non-nulles
        for i in range(min(52, len(blendshapes))):
            value = blendshapes[i]
            if value > 0.001:  # Seuil pour ignorer les valeurs négligeables
                py_face._blend_shapes[i] = max(0.0, min(1.0, value))
        
        # Encoder et envoyer directement
        socket_connection.sendall(py_face.encode())
        
    except Exception as e:
        if DEBUG_MODE:
            logger.error(f"Erreur LiveLink: {e}")

@app.route('/health', methods=['GET'])
def health():
    """Endpoint de santé minimal"""
    return jsonify({
        "status": "healthy",
        "performance_mode": PERFORMANCE_MODE,
        "debug_mode": DEBUG_MODE,
        "model_loaded": blendshape_model is not None,
        "livelink_connected": socket_connection is not None
    })

@app.route('/audio_to_blendshapes', methods=['POST'])
def audio_to_blendshapes_route():
    """Endpoint principal optimisé"""
    try:
        # Récupérer les données audio
        audio_bytes = request.data
        
        if not audio_bytes:
            return jsonify({"status": "error", "message": "No audio data"}), 400
        
        # Log minimal en mode debug seulement
        if DEBUG_MODE:
            logger.debug(f"Audio reçu: {len(audio_bytes)} octets")
        
        # Traitement des blendshapes
        device = "cuda" if torch.cuda.is_available() else "cpu"
        generated_facial_data = generate_facial_data_from_bytes(
            audio_bytes, 
            blendshape_model, 
            device, 
            config
        )
        
        # Conversion rapide
        if isinstance(generated_facial_data, np.ndarray):
            blendshapes = generated_facial_data.tolist()
        else:
            blendshapes = generated_facial_data
        
        # Envoi direct à LiveLink
        if blendshapes:
            if isinstance(blendshapes, list):
                if isinstance(blendshapes[0], list):
                    # Multiple frames - envoyer rapidement
                    for frame in blendshapes:
                        send_to_livelink_optimized(frame)
                        if PERFORMANCE_MODE:
                            # Pas de sleep en mode performance
                            pass
                        else:
                            time.sleep(0.016)  # ~60 FPS
                else:
                    # Frame unique
                    send_to_livelink_optimized(blendshapes)
        
        # Réponse minimale en mode performance
        if PERFORMANCE_MODE:
            return jsonify({'status': 'ok'})
        else:
            return jsonify({'blendshapes': blendshapes})
    
    except Exception as e:
        logger.error(f"Erreur: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Mode performance : désactiver les endpoints de debug
if not DEBUG_MODE:
    @app.route('/debug/<path:path>', methods=['GET', 'POST'])
    def debug_disabled(path):
        return jsonify({"error": "Debug mode disabled"}), 404

if __name__ == '__main__':
    print(f"\n{'='*50}")
    print(f"🚀 API OPTIMISÉE - Mode: {'DEBUG' if DEBUG_MODE else 'PERFORMANCE'}")
    print(f"{'='*50}\n")
    
    # Initialisation
    load_neurosync_model()
    init_livelink()
    
    # Optimisations CUDA
    if torch.cuda.is_available():
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.deterministic = False
    
    print(f"API en écoute sur le port {API_PORT}")
    print(f"LiveLink: {LIVELINK_IP}:{LIVELINK_PORT}")
    
    if PERFORMANCE_MODE:
        print("\n⚡ MODE PERFORMANCE ACTIVÉ")
        print("Logging minimal pour éviter les saccades")
        print("Pour activer le debug: export DEBUG_MODE=ON")
    else:
        print("\n🔍 MODE DEBUG ACTIVÉ")
        print("Pour le mode performance: export PERFORMANCE_MODE=ON")
    
    print(f"\n{'='*50}\n")
    
    # Lancer sans debug Flask
    app.run(host='0.0.0.0', port=API_PORT, debug=False, threaded=True)