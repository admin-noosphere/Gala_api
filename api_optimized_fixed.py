#!/usr/bin/env python3
"""
API optimisée avec gestion audio fixée et contrôle des ressources
"""

import os
import sys
import socket
import logging
import warnings
import numpy as np
import wave
import io
import time
warnings.filterwarnings("ignore")

from flask import Flask, request, jsonify
from datetime import datetime

# Configuration GPU
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

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

# Logging minimal
logging.basicConfig(level=logging.INFO, format='%(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Variables globales
blendshape_model = None
py_face = None
socket_connection = None
last_process_time = time.time()

def create_wav_from_pcm(pcm_data, sample_rate=16000):
    """Crée un fichier WAV à partir de données PCM brutes"""
    wav_buffer = io.BytesIO()
    
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)
    
    wav_buffer.seek(0)
    return wav_buffer.read()

def process_audio_input(audio_bytes):
    """Traite l'audio d'entrée et s'assure qu'il est au format WAV"""
    # Vérifier si c'est déjà du WAV
    if audio_bytes.startswith(b'RIFF'):
        return audio_bytes
    
    # Sinon, c'est probablement du PCM brut
    logger.info("Audio PCM brut détecté, conversion en WAV")
    
    # Toujours utiliser 16kHz pour Gala
    return create_wav_from_pcm(audio_bytes, 16000)

def load_neurosync_model():
    """Charge le modèle NeuroSync"""
    global blendshape_model
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Chargement du modèle NeuroSync sur {device}")
    
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

def send_to_livelink_fast(blendshapes):
    """Envoi rapide à LiveLink avec debug optionnel"""
    global py_face, socket_connection
    
    if not py_face or not socket_connection:
        return
    
    try:
        # Reset
        for i in range(52):
            py_face._blend_shapes[i] = 0.0
        
        # Appliquer les valeurs
        active_shapes = []
        for i in range(min(52, len(blendshapes))):
            value = blendshapes[i]
            if value > 0.001:
                py_face._blend_shapes[i] = max(0.0, min(1.0, value))
                if value > 0.1:  # Seulement logger les valeurs significatives
                    active_shapes.append((i, value))
        
        # Debug si nécessaire
        if active_shapes and len(active_shapes) < 10:
            logger.debug(f"Shapes actifs: {active_shapes}")
        
        # Envoyer
        socket_connection.sendall(py_face.encode())
        
    except Exception as e:
        logger.error(f"Erreur LiveLink: {e}")

@app.route('/health', methods=['GET'])
def health():
    """Endpoint de santé"""
    return jsonify({
        "status": "healthy",
        "model_loaded": blendshape_model is not None,
        "livelink_connected": socket_connection is not None,
        "last_process_time": time.time() - last_process_time
    })

@app.route('/audio_to_blendshapes', methods=['POST'])
def audio_to_blendshapes_route():
    """Endpoint principal avec gestion optimisée"""
    global last_process_time
    
    try:
        # Limiter le taux de traitement
        current_time = time.time()
        if current_time - last_process_time < 0.03:  # Max 33 FPS
            time.sleep(0.03 - (current_time - last_process_time))
        
        # Récupérer les données audio
        audio_bytes = request.data
        
        if not audio_bytes:
            return jsonify({"status": "error", "message": "No audio data"}), 400
        
        # Convertir l'audio
        wav_data = process_audio_input(audio_bytes)
        
        # Traitement des blendshapes
        device = "cuda" if torch.cuda.is_available() else "cpu"
        generated_facial_data = generate_facial_data_from_bytes(
            wav_data, 
            blendshape_model, 
            device, 
            config
        )
        
        # Conversion si nécessaire
        if isinstance(generated_facial_data, np.ndarray):
            blendshapes = generated_facial_data.tolist()
        else:
            blendshapes = generated_facial_data
        
        # Envoi à LiveLink
        if blendshapes:
            if isinstance(blendshapes, list):
                if isinstance(blendshapes[0], list):
                    # Multiple frames
                    for frame in blendshapes:
                        send_to_livelink_fast(frame)
                else:
                    # Frame unique
                    send_to_livelink_fast(blendshapes)
        
        last_process_time = time.time()
        
        # Retourner plus d'infos si debug activé
        debug = request.headers.get('X-Debug', '').lower() == 'true'
        if debug:
            return jsonify({
                'status': 'ok',
                'debug': {
                    'blendshape_count': len(blendshapes) if isinstance(blendshapes, list) else 0,
                    'processing_time': time.time() - current_time
                }
            })
        
        return jsonify({'status': 'ok'})
    
    except Exception as e:
        logger.error(f"Erreur: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/test_blendshapes', methods=['GET'])
def test_blendshapes():
    """Endpoint de test pour envoyer des blendshapes manuels"""
    try:
        # Créer des blendshapes de test
        test_blendshapes = [0.0] * 52
        
        # Activer quelques blendshapes pour test
        test_blendshapes[17] = 0.5  # JawOpen
        test_blendshapes[23] = 0.3  # MouthSmileLeft
        test_blendshapes[24] = 0.3  # MouthSmileRight
        
        send_to_livelink_fast(test_blendshapes)
        
        return jsonify({
            'status': 'ok',
            'sent': {
                'JawOpen': 0.5,
                'MouthSmileLeft': 0.3,
                'MouthSmileRight': 0.3
            }
        })
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 API GALA - Optimisée")
    print("="*50 + "\n")
    
    # Initialisation
    load_neurosync_model()
    init_livelink()
    
    # Optimisations CUDA
    if torch.cuda.is_available():
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.benchmark = True
        torch.cuda.set_per_process_memory_fraction(0.8)  # Limiter la mémoire GPU
    
    print(f"API en écoute sur le port {API_PORT}")
    print(f"LiveLink: {LIVELINK_IP}:{LIVELINK_PORT}")
    print("\n" + "="*50 + "\n")
    
    # Utiliser le serveur de production
    from werkzeug.serving import run_simple
    run_simple('0.0.0.0', API_PORT, app, threaded=True)