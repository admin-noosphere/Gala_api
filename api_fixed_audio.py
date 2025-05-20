#!/usr/bin/env python3
"""
API avec gestion audio fixée
Gère correctement les formats PCM bruts
"""

import os
import sys
import socket
import logging
import warnings
import numpy as np
import wave
import io
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

def create_wav_from_pcm(pcm_data, sample_rate=16000):
    """
    Crée un fichier WAV à partir de données PCM brutes
    """
    # Créer un buffer WAV en mémoire
    wav_buffer = io.BytesIO()
    
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)
    
    wav_buffer.seek(0)
    return wav_buffer.read()

def process_audio_input(audio_bytes):
    """
    Traite l'audio d'entrée et s'assure qu'il est au format WAV
    """
    # Vérifier si c'est déjà du WAV
    if audio_bytes.startswith(b'RIFF'):
        logger.info("Audio déjà au format WAV")
        return audio_bytes
    
    # Sinon, c'est probablement du PCM brut
    logger.info("Audio PCM brut détecté, conversion en WAV")
    
    # Détecter le sample rate basé sur la taille
    # Gala envoie probablement du 16kHz mono 16-bit
    num_samples = len(audio_bytes) // 2  # 2 bytes per sample
    duration_guess = num_samples / 16000  # Assume 16kHz
    
    if duration_guess < 0.1:  # Très court, essayer 48kHz
        sample_rate = 48000
    elif duration_guess > 10:  # Très long, essayer 8kHz
        sample_rate = 8000
    else:
        sample_rate = 16000  # Par défaut
    
    logger.info(f"Utilisation du sample rate: {sample_rate}Hz")
    
    return create_wav_from_pcm(audio_bytes, sample_rate)

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
    """Envoi rapide à LiveLink"""
    global py_face, socket_connection
    
    if not py_face or not socket_connection:
        return
    
    try:
        # Reset rapide
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

@app.route('/health', methods=['GET'])
def health():
    """Endpoint de santé"""
    return jsonify({
        "status": "healthy",
        "model_loaded": blendshape_model is not None,
        "livelink_connected": socket_connection is not None
    })

@app.route('/audio_to_blendshapes', methods=['POST'])
def audio_to_blendshapes_route():
    """Endpoint principal avec gestion audio fixée"""
    try:
        # Récupérer les données audio
        audio_bytes = request.data
        
        if not audio_bytes:
            return jsonify({"status": "error", "message": "No audio data"}), 400
        
        # Convertir l'audio au bon format
        try:
            wav_data = process_audio_input(audio_bytes)
        except Exception as e:
            logger.error(f"Erreur conversion audio: {e}")
            # Fallback: essayer directement comme PCM 16kHz
            wav_data = create_wav_from_pcm(audio_bytes, 16000)
        
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
        
        return jsonify({'status': 'ok'})
    
    except Exception as e:
        logger.error(f"Erreur: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 API GALA - Audio Fix")
    print("="*50 + "\n")
    
    # Initialisation
    load_neurosync_model()
    init_livelink()
    
    # Optimisations CUDA
    if torch.cuda.is_available():
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.benchmark = True
    
    print(f"API en écoute sur le port {API_PORT}")
    print(f"LiveLink: {LIVELINK_IP}:{LIVELINK_PORT}")
    print("\n" + "="*50 + "\n")
    
    app.run(host='0.0.0.0', port=API_PORT, debug=False, threaded=True)