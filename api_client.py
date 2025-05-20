#!/usr/bin/env python3
"""
Gala v1 - API Client Unifiée
Fusion de NeuroSync Player et Real-Time API
Converti audio stream -> blendshapes -> LiveLink
"""

import asyncio
import json
import time
import numpy as np
import torch
import torchaudio
import websockets
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import List, Dict, Optional

# Import des modules NeuroSync
from modules.neurosync_simple import NeuroSyncSimple
from modules.audio_processor import AudioProcessor
from modules.livelink_client import LiveLinkClient

app = Flask(__name__)
CORS(app)

# Configuration globale
CONFIG = {
    "sample_rate": 48000,  # Standard pour Player
    "audio_format": "int16",
    "channels": 1,  # Mono
    "min_audio_ms": 200,  # Accumulation minimale
    "target_fps": 60,
    "blendshapes_count": 68,
    "model_path": "models/neurosync/model/model.pth",
    "livelink_port": 11111,
    "api_port": 6969
}

# Ajouter un endpoint de santé
@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint pour vérifier que l'API est en cours d'exécution"""
    return jsonify({
        "status": "ok",
        "api_version": "1.0",
        "model_loaded": model is not None
    })

# Initialisation des composants
model = None
audio_processor = None
livelink_client = None

# Liste des 68 blendshapes ARKit standard
BLENDSHAPE_NAMES = [
    "EyeBlink_L", "EyeBlink_R", "EyeLookDown_L", "EyeLookDown_R",
    "EyeLookIn_L", "EyeLookIn_R", "EyeLookOut_L", "EyeLookOut_R",
    "EyeLookUp_L", "EyeLookUp_R", "EyeSquint_L", "EyeSquint_R",
    "EyeWide_L", "EyeWide_R", "JawForward", "JawLeft", "JawRight",
    "JawOpen", "MouthClose", "MouthFunnel", "MouthPucker", "MouthLeft",
    "MouthRight", "MouthSmile_L", "MouthSmile_R", "MouthFrown_L",
    "MouthFrown_R", "MouthDimple_L", "MouthDimple_R", "MouthStretch_L",
    "MouthStretch_R", "MouthRollLower", "MouthRollUpper", "MouthShrugLower",
    "MouthShrugUpper", "MouthPress_L", "MouthPress_R", "MouthLowerDown_L",
    "MouthLowerDown_R", "MouthUpperUp_L", "MouthUpperUp_R", "BrowDown_L",
    "BrowDown_R", "BrowInnerUp", "BrowOuterUp_L", "BrowOuterUp_R",
    "CheekPuff", "CheekSquint_L", "CheekSquint_R", "NoseSneer_L",
    "NoseSneer_R", "TongueOut", "HeadYaw", "HeadPitch", "HeadRoll",
    "EyeBlinkLeft", "EyeBlinkRight", "EyeOpenLeft", "EyeOpenRight",
    "BrowLeftDown", "BrowLeftUp", "BrowRightDown", "BrowRightUp",
    "EmotionHappy", "EmotionSad", "EmotionAngry", "EmotionSurprised"
]

@app.route('/health', methods=['GET'])
def health():
    """
    Endpoint de santé pour vérifier que l'API est en ligne
    """
    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "model": "NeuroSync v3",
        "config": {
            "sample_rate": CONFIG["sample_rate"],
            "livelink_port": CONFIG["livelink_port"],
            "api_port": CONFIG["api_port"]
        }
    })

@app.route('/audio_to_blendshapes', methods=['POST'])
def audio_to_blendshapes():
    """
    Endpoint principal : convertit audio en blendshapes
    Input: audio WAV (48kHz, mono, 16-bit)
    Output: 68 blendshapes float32
    """
    try:
        # Récupérer l'audio depuis la requête
        audio_data = request.data
        
        # Traiter l'audio
        audio_np = np.frombuffer(audio_data, dtype=np.int16)
        audio_float = audio_np.astype(np.float32) / 32768.0
        
        # Rééchantillonner si nécessaire pour le modèle (88200Hz)
        if CONFIG["sample_rate"] != 88200:
            resampler = torchaudio.transforms.Resample(
                orig_freq=CONFIG["sample_rate"],
                new_freq=88200
            )
            audio_tensor = torch.FloatTensor(audio_float).unsqueeze(0)
            audio_resampled = resampler(audio_tensor).squeeze(0).numpy()
        else:
            audio_resampled = audio_float
            
        # Convertir en tensor
        audio_tensor = torch.FloatTensor(audio_resampled).unsqueeze(0)
        
        # Inférence avec le modèle via le wrapper
        blendshapes = model.process_audio(audio_tensor)
            
        # Convertir en liste float
        blendshapes_list = blendshapes.cpu().numpy().tolist()[0]
        
        return jsonify({
            "blendshapes": blendshapes_list,
            "blendshape_names": BLENDSHAPE_NAMES,
            "timestamp": time.time(),
            "fps": CONFIG["target_fps"]
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stream_audio', methods=['POST'])
async def stream_audio():
    """
    Endpoint streaming : audio -> blendshapes -> LiveLink
    Accumule l'audio avant traitement
    """
    try:
        # Buffer d'accumulation
        audio_buffer = audio_processor.get_buffer()
        
        # Ajouter l'audio reçu au buffer
        audio_data = request.data
        audio_buffer.append(audio_data)
        
        # Vérifier si on a assez d'audio (200ms min)
        min_samples = int(CONFIG["sample_rate"] * CONFIG["min_audio_ms"] / 1000)
        buffer_size = sum(len(chunk) for chunk in audio_buffer)
        
        if buffer_size >= min_samples * 2:  # int16 = 2 bytes
            # Combiner le buffer
            combined_audio = b''.join(audio_buffer)
            audio_buffer.clear()
            
            # Traiter l'audio
            response = audio_to_blendshapes_internal(combined_audio)
            blendshapes = response["blendshapes"]
            
            # Envoyer à LiveLink
            await livelink_client.send_blendshapes(blendshapes)
            
            return jsonify({
                "status": "sent_to_livelink",
                "blendshapes_count": len(blendshapes),
                "timestamp": time.time()
            })
        else:
            return jsonify({
                "status": "buffering",
                "buffer_ms": buffer_size / (CONFIG["sample_rate"] * 2) * 1000
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def audio_to_blendshapes_internal(audio_data: bytes) -> Dict:
    """Version interne pour le streaming"""
    audio_np = np.frombuffer(audio_data, dtype=np.int16)
    audio_float = audio_np.astype(np.float32) / 32768.0
    
    if CONFIG["sample_rate"] != 88200:
        resampler = torchaudio.transforms.Resample(
            orig_freq=CONFIG["sample_rate"],
            new_freq=88200
        )
        audio_tensor = torch.FloatTensor(audio_float).unsqueeze(0)
        audio_resampled = resampler(audio_tensor).squeeze(0).numpy()
    else:
        audio_resampled = audio_float
        
    audio_tensor = torch.FloatTensor(audio_resampled).unsqueeze(0)
    
    blendshapes = model.process_audio(audio_tensor)
        
    return {
        "blendshapes": blendshapes.cpu().numpy().tolist()[0],
        "blendshape_names": BLENDSHAPE_NAMES
    }

def init_components():
    """Initialise les composants de l'API"""
    global model, audio_processor, livelink_client
    
    print("Initialisation des composants...")
    
    # Charger le modèle NeuroSync avec NeuroSyncWrapper
    model = NeuroSyncSimple(CONFIG["model_path"], device="cuda" if torch.cuda.is_available() else "cpu")
    
    # Initialiser le processeur audio
    audio_processor = AudioProcessor(CONFIG)
    
    # Initialiser le client LiveLink avec la bonne IP
    livelink_client = LiveLinkClient(
        host="192.168.1.14",  # IP d'Unreal Engine
        port=CONFIG["livelink_port"],
        fps=CONFIG["target_fps"]
    )
    
    print("Composants initialisés avec succès")

if __name__ == "__main__":
    init_components()
    app.run(
        host="0.0.0.0", 
        port=CONFIG["api_port"],
        debug=True
    )
