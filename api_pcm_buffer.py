#!/usr/bin/env python3
"""
API optimisée avec PCM direct et système de buffer
192ms de données audio avant traitement
"""

import os
import sys
import socket
import logging
import warnings
import numpy as np
import time
import threading
from collections import deque
warnings.filterwarnings("ignore")

from flask import Flask, request, jsonify
from datetime import datetime

# Configuration GPU 1
os.environ["CUDA_VISIBLE_DEVICES"] = "1"

import torch

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

# Configuration audio
SAMPLE_RATE = 16000  # Gala envoie du 16kHz
BUFFER_DURATION_MS = 192  # Durée du buffer en ms
BUFFER_SIZE = int(SAMPLE_RATE * BUFFER_DURATION_MS / 1000 * 2)  # *2 pour 16-bit

# Logging minimal
logging.basicConfig(level=logging.INFO, format='%(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Variables globales
blendshape_model = None
py_face = None
socket_connection = None
audio_buffer = bytearray()
buffer_lock = threading.Lock()
processing_thread = None
running = True

def load_neurosync_model():
    """Charge le modèle NeuroSync"""
    global blendshape_model
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Chargement du modèle NeuroSync sur {device} (GPU {os.environ.get('CUDA_VISIBLE_DEVICES', 'default')})")
    
    model_path = os.path.join(neurosync_path, 'models/neurosync/model/model.pth')
    blendshape_model = load_model(model_path, config, device)
    
    logger.info("✅ Modèle chargé")
    return blendshape_model

def init_livelink():
    """Initialise la connexion LiveLink"""
    global py_face, socket_connection
    
    logger.info(f"Connexion LiveLink vers {LIVELINK_IP}:{LIVELINK_PORT}")
    
    py_face = PyLiveLinkFace(name="GalaFace", fps=60)
    socket_connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_connection.connect((LIVELINK_IP, LIVELINK_PORT))
    
    logger.info("✅ LiveLink connecté")

def send_to_livelink(blendshapes):
    """Envoi des blendshapes à LiveLink"""
    global py_face, socket_connection
    
    if not py_face or not socket_connection:
        return
    
    try:
        # Reset
        for i in range(52):
            py_face._blend_shapes[i] = 0.0
        
        # Appliquer les valeurs
        for i in range(min(52, len(blendshapes))):
            value = blendshapes[i]
            if value > 0.001:
                py_face._blend_shapes[i] = max(0.0, min(1.0, value))
        
        # Envoyer
        socket_connection.sendall(py_face.encode())
        
    except Exception as e:
        logger.error(f"Erreur LiveLink: {e}")

def process_audio_buffer():
    """Thread de traitement du buffer audio"""
    global running, audio_buffer, buffer_lock
    
    logger.info("Thread de traitement audio démarré")
    
    while running:
        try:
            # Attendre d'avoir assez de données
            with buffer_lock:
                if len(audio_buffer) >= BUFFER_SIZE:
                    # Extraire le buffer
                    audio_data = bytes(audio_buffer[:BUFFER_SIZE])
                    audio_buffer[:BUFFER_SIZE] = []  # Retirer les données traitées
                else:
                    time.sleep(0.01)  # Attendre plus de données
                    continue
            
            # Traiter les données PCM directement
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # NeuroSync accepte directement le PCM
            generated_facial_data = generate_facial_data_from_bytes(
                audio_data, 
                blendshape_model, 
                device, 
                config
            )
            
            # Envoyer les blendshapes
            if generated_facial_data is not None:
                if isinstance(generated_facial_data, np.ndarray):
                    blendshapes = generated_facial_data.tolist()
                else:
                    blendshapes = generated_facial_data
                
                if isinstance(blendshapes, list):
                    if isinstance(blendshapes[0], list):
                        # Multiple frames
                        for frame in blendshapes:
                            send_to_livelink(frame)
                            time.sleep(0.016)  # ~60 FPS
                    else:
                        # Frame unique
                        send_to_livelink(blendshapes)
            
        except Exception as e:
            logger.error(f"Erreur traitement buffer: {e}")
            time.sleep(0.1)

@app.route('/health', methods=['GET'])
def health():
    """Endpoint de santé"""
    with buffer_lock:
        buffer_level = len(audio_buffer)
    
    return jsonify({
        "status": "healthy",
        "model_loaded": blendshape_model is not None,
        "livelink_connected": socket_connection is not None,
        "gpu": os.environ.get('CUDA_VISIBLE_DEVICES', 'default'),
        "buffer_level": buffer_level,
        "buffer_max": BUFFER_SIZE
    })

@app.route('/audio_to_blendshapes', methods=['POST'])
def audio_to_blendshapes_route():
    """Endpoint principal - ajoute au buffer audio"""
    global audio_buffer
    
    try:
        # Récupérer les données audio PCM
        audio_bytes = request.data
        
        if not audio_bytes:
            return jsonify({"status": "error", "message": "No audio data"}), 400
        
        # Ajouter au buffer
        with buffer_lock:
            audio_buffer.extend(audio_bytes)
            buffer_level = len(audio_buffer)
        
        # Logger occasionnellement le niveau du buffer
        if buffer_level % (BUFFER_SIZE // 2) < len(audio_bytes):
            logger.debug(f"Buffer: {buffer_level}/{BUFFER_SIZE} bytes")
        
        return jsonify({
            'status': 'ok',
            'buffered': len(audio_bytes),
            'buffer_level': buffer_level
        })
    
    except Exception as e:
        logger.error(f"Erreur: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/flush_buffer', methods=['POST'])
def flush_buffer():
    """Force le traitement du buffer même s'il n'est pas plein"""
    global audio_buffer
    
    with buffer_lock:
        if len(audio_buffer) > 0:
            # Traiter ce qu'il y a dans le buffer
            logger.info(f"Flush du buffer: {len(audio_buffer)} bytes")
            audio_buffer.clear()
    
    return jsonify({'status': 'ok', 'flushed': True})

def cleanup():
    """Nettoyage lors de l'arrêt"""
    global running, socket_connection
    
    running = False
    if processing_thread:
        processing_thread.join(timeout=2)
    
    if socket_connection:
        socket_connection.close()

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 API GALA - PCM Direct avec Buffer")
    print("="*50 + "\n")
    
    # Initialisation
    load_neurosync_model()
    init_livelink()
    
    # Démarrer le thread de traitement
    processing_thread = threading.Thread(target=process_audio_buffer)
    processing_thread.start()
    
    # Optimisations CUDA
    if torch.cuda.is_available():
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.benchmark = True
    
    print(f"API en écoute sur le port {API_PORT}")
    print(f"LiveLink: {LIVELINK_IP}:{LIVELINK_PORT}")
    print(f"Buffer: {BUFFER_DURATION_MS}ms ({BUFFER_SIZE} bytes)")
    print(f"GPU utilisé: {os.environ.get('CUDA_VISIBLE_DEVICES', 'default')}")
    print("\n" + "="*50 + "\n")
    
    try:
        app.run(host='0.0.0.0', port=API_PORT, debug=False, threaded=True)
    finally:
        cleanup()