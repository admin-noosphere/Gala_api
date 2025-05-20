#!/usr/bin/env python3
"""
API Clone exacte de NeuroSync Real-Time API
Reproduit le comportement exact de l'API originale pour la génération de blendshapes
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

# Ajouter le chemin NeuroSync au PYTHONPATH
neurosync_path = "/home/gieidi-prime/Agents/NeuroSync_Local_API/neurosync_v3_all copy/NeuroSync_Real-Time_API"
sys.path.insert(0, neurosync_path)

# Imports NeuroSync (exactement comme dans l'original)
from models.neurosync.config import config
from models.neurosync.generate_face_shapes import generate_facial_data_from_bytes
from models.neurosync.model.model import load_model

# Module LiveLink from Gala v1
sys.path.append('/home/gieidi-prime/Agents/Claude/Gala_v1')
from modules.pylivelinkface import PyLiveLinkFace, FaceBlendShape

# Configuration
LIVELINK_IP = "192.168.1.14"
LIVELINK_PORT = 11111
API_PORT = 6969

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Optimisations CUDA (comme dans l'original)
if torch.cuda.is_available():
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.benchmark = True

# Flask app
app = Flask(__name__)

# Variables globales pour le modèle et LiveLink
blendshape_model = None
py_face = None
socket_connection = None

def load_neurosync_model():
    """Charge le modèle NeuroSync exactement comme l'API originale"""
    global blendshape_model
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Chargement du modèle NeuroSync sur {device}")
    
    # Charger le modèle comme dans l'original
    model_path = os.path.join(neurosync_path, 'models/neurosync/model/model.pth')
    blendshape_model = load_model(model_path, config, device)
    
    logger.info("Modèle NeuroSync chargé avec succès")
    return blendshape_model

def init_livelink():
    """Initialise la connexion LiveLink"""
    global py_face, socket_connection
    
    logger.info(f"Initialisation LiveLink vers {LIVELINK_IP}:{LIVELINK_PORT}")
    
    py_face = PyLiveLinkFace(name="GalaFace", fps=60)
    socket_connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_connection.connect((LIVELINK_IP, LIVELINK_PORT))
    
    logger.info("LiveLink initialisé avec succès")

def send_to_livelink(blendshapes):
    """Envoie les blendshapes à Unreal via LiveLink"""
    global py_face, socket_connection
    
    if not py_face or not socket_connection:
        logger.error("LiveLink non initialisé")
        return
    
    try:
        # Reset tous les blendshapes
        for i in range(52):  # 0-51 valides
            py_face.set_blendshape(FaceBlendShape(i), 0.0)
        
        # Appliquer les nouvelles valeurs
        for i in range(min(52, len(blendshapes))):
            value = float(blendshapes[i])
            # Limiter entre 0 et 1
            value = max(0.0, min(1.0, value))
            py_face.set_blendshape(FaceBlendShape(i), value)
        
        # Encoder et envoyer
        data = py_face.encode()
        socket_connection.sendall(data)
        
    except Exception as e:
        logger.error(f"Erreur LiveLink: {e}")

@app.route('/health', methods=['GET'])
def health():
    """Endpoint de santé"""
    return jsonify({
        "status": "healthy",
        "api_version": "1.0.0",
        "model_loaded": blendshape_model is not None,
        "livelink_connected": socket_connection is not None,
        "config": {
            "port": API_PORT,
            "livelink_ip": LIVELINK_IP,
            "livelink_port": LIVELINK_PORT
        }
    })

@app.route('/audio_to_blendshapes', methods=['POST'])
def audio_to_blendshapes_route():
    """Endpoint principal - reproduit exactement l'API originale"""
    try:
        # Récupérer les données audio
        audio_bytes = request.data
        content_type = request.headers.get('Content-Type', 'unknown')
        content_length = len(audio_bytes) if audio_bytes else 0
        
        logger.info(f"📥 Requête reçue : {content_length} octets, Content-Type: {content_type}")
        
        if not audio_bytes:
            msg = "No audio data provided."
            logger.error(f"❌ Erreur : {msg}")
            return jsonify({"status": "error", "message": msg}), 400
        
        # Afficher les 20 premiers octets pour debug
        logger.info(f"⚙️ Début des données audio : {audio_bytes[:20]}")
        
        # Traitement des blendshapes (exactement comme l'original)
        logger.info(f"🔄 Traitement des blendshapes en cours...")
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        generated_facial_data = generate_facial_data_from_bytes(
            audio_bytes, 
            blendshape_model, 
            device, 
            config
        )
        
        # Convertir en liste si c'est un numpy array
        if isinstance(generated_facial_data, np.ndarray):
            blendshapes = generated_facial_data.tolist()
        else:
            blendshapes = generated_facial_data
        
        # Logs de debug comme l'original
        if blendshapes:
            blendshape_count = len(blendshapes)
            blendshape_type = type(blendshapes).__name__
            
            if isinstance(blendshapes, list) and len(blendshapes) > 0:
                first_frame = blendshapes[0] if len(blendshapes) > 0 else []
                logger.info(f"✅ Blendshapes générés : {blendshape_count} frames, type: {blendshape_type}")
                
                # Pour une liste de frames
                if isinstance(first_frame, list):
                    logger.info(f"📊 Premier frame (échantillon) : {first_frame[:5]}...")
                    logger.info(f"📏 Nombre de valeurs par frame : {len(first_frame)}")
                    
                    # Envoyer la première frame à LiveLink pour test
                    send_to_livelink(first_frame)
                    
                # Pour une simple liste de valeurs
                else:
                    logger.info(f"📊 Blendshapes (échantillon) : {blendshapes[:5]}...")
                    logger.info(f"📏 Nombre total de valeurs : {len(blendshapes)}")
                    
                    # Envoyer directement à LiveLink
                    send_to_livelink(blendshapes)
            else:
                logger.warning(f"⚠️ Format de blendshapes inhabituel : {blendshape_type}")
        else:
            logger.error(f"❌ Pas de blendshapes générés")
        
        # Retourner le résultat comme l'API originale
        result = {'blendshapes': blendshapes}
        logger.info(f"📤 Envoi de la réponse : {len(str(result))} caractères")
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"❌❌❌ Exception critique: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Initialisation
    logger.info("=== Démarrage de l'API Real-Time Clone ===")
    
    # Charger le modèle
    load_neurosync_model()
    
    # Initialiser LiveLink
    init_livelink()
    
    # Lancer l'API
    logger.info(f"API en écoute sur le port {API_PORT}")
    app.run(host='0.0.0.0', port=API_PORT, debug=False)