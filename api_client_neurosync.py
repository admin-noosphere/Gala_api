#!/usr/bin/env python3
"""
Gala v1 - API Client Unifiée avec envoi LiveLink style NeuroSync
Fusion de NeuroSync Player et Real-Time API
Converti audio stream -> blendshapes -> LiveLink
"""

import json
import time
import socket
import numpy as np
import torch
import torchaudio
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import List, Dict, Optional

# Import des modules NeuroSync
from modules.neurosync_simple import NeuroSyncSimple
from modules.audio_processor import AudioProcessor
from modules.livelink_neurosync import LiveLinkNeuroSync  # Utiliser notre module validé
from modules.pylivelinkface import PyLiveLinkFace, FaceBlendShape

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
    "api_port": 6969,
    "livelink_ip": "192.168.1.14"  # IP d'Unreal Engine
}

# Initialisation des composants
model = None
audio_processor = None
livelink = None
py_face = None
socket_connection = None

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
        "livelink_connected": socket_connection is not None,
        "config": {
            "sample_rate": CONFIG["sample_rate"],
            "livelink_port": CONFIG["livelink_port"],
            "livelink_ip": CONFIG["livelink_ip"],
            "api_port": CONFIG["api_port"]
        }
    })

@app.route('/audio_to_blendshapes', methods=['POST'])
def audio_to_blendshapes():
    """
    Endpoint principal : convertit audio en blendshapes et envoie à LiveLink
    Input: audio WAV (48kHz, mono, 16-bit)
    Output: 68 blendshapes float32 + envoi direct à Unreal
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
        
        # Envoyer directement à LiveLink comme dans test_neurosync_livelink
        send_to_livelink_direct(blendshapes_list)
        
        return jsonify({
            "blendshapes": blendshapes_list,
            "blendshape_names": BLENDSHAPE_NAMES,
            "timestamp": time.time(),
            "fps": CONFIG["target_fps"],
            "sent_to_livelink": True
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stream_audio', methods=['POST'])
def stream_audio():
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
            
            # Envoyer à LiveLink directement
            send_to_livelink_direct(blendshapes)
            
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

def send_to_livelink_direct(blendshapes: List[float]):
    """
    Envoie les blendshapes à LiveLink en utilisant l'approche validée
    Utilise pylivelinkface comme dans wave_to_face.py
    """
    global py_face, socket_connection
    
    if len(blendshapes) != 68:
        raise ValueError(f"Expected 68 blendshapes, got {len(blendshapes)}")
    
    # Envoyer avec l'approche LiveLinkNeuroSync
    if livelink:
        livelink.send_blendshapes(blendshapes)
    else:
        # Fallback: utiliser directement PyLiveLinkFace et socket
        if py_face and socket_connection:
            # Reset des blendshapes
            for i in range(52):  # Seulement 0-51 valides
                py_face.set_blendshape(FaceBlendShape(i), 0.0)
            
            # Appliquer les nouvelles valeurs (68 -> 52)
            for i in range(min(52, len(blendshapes))):
                py_face.set_blendshape(FaceBlendShape(i), blendshapes[i])
            
            # Encoder et envoyer
            data = py_face.encode()
            socket_connection.sendall(data)

def init_components():
    """Initialise les composants de l'API"""
    global model, audio_processor, livelink, py_face, socket_connection
    
    print("Initialisation des composants...")
    
    # Charger le modèle NeuroSync avec NeuroSyncWrapper
    model = NeuroSyncSimple(CONFIG["model_path"], device="cuda" if torch.cuda.is_available() else "cpu")
    
    # Initialiser le processeur audio
    audio_processor = AudioProcessor(CONFIG)
    
    # Initialiser LiveLink avec notre approche validée
    try:
        livelink = LiveLinkNeuroSync(
            udp_ip=CONFIG["livelink_ip"],
            udp_port=CONFIG["livelink_port"],
            fps=CONFIG["target_fps"]
        )
        print(f"LiveLink connecté à {CONFIG['livelink_ip']}:{CONFIG['livelink_port']}")
    except Exception as e:
        print(f"Erreur LiveLink: {e}")
        
        # Fallback: créer directement PyLiveLinkFace et socket
        py_face = PyLiveLinkFace(name="GalaFace", fps=CONFIG["target_fps"])
        socket_connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socket_connection.connect((CONFIG["livelink_ip"], CONFIG["livelink_port"]))
        print("Utilisation du mode socket direct")
    
    print("Composants initialisés avec succès")

if __name__ == "__main__":
    init_components()
    app.run(
        host="0.0.0.0", 
        port=CONFIG["api_port"],
        debug=True
    )