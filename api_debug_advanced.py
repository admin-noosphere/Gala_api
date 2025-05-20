#!/usr/bin/env python3
"""
API avec système de debugging avancé pour diagnostiquer les problèmes LiveLink
Inclut logging détaillé, validation et comparaison des formats
"""

import os
import sys
import json
import time
import struct
import socket
import logging
import warnings
import numpy as np
from datetime import datetime
from pathlib import Path
warnings.filterwarnings("ignore")

from flask import Flask, request, jsonify
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.io as pio

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
DEBUG_DIR = Path("debug_logs")
DEBUG_DIR.mkdir(exist_ok=True)

# Logging avancé
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
    handlers=[
        logging.FileHandler(DEBUG_DIR / f'api_debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Variables globales
blendshape_model = None
py_face = None
socket_connection = None
frame_counter = 0

# Mapping des blendshapes pour debug
BLENDSHAPE_NAMES = [
    "EyeBlinkLeft", "EyeLookDownLeft", "EyeLookInLeft", "EyeLookOutLeft", "EyeLookUpLeft", 
    "EyeSquintLeft", "EyeWideLeft", "EyeBlinkRight", "EyeLookDownRight", "EyeLookInRight",
    "EyeLookOutRight", "EyeLookUpRight", "EyeSquintRight", "EyeWideRight", "JawForward",
    "JawLeft", "JawRight", "JawOpen", "MouthClose", "MouthFunnel", "MouthPucker",
    "MouthLeft", "MouthRight", "MouthSmileLeft", "MouthSmileRight", "MouthFrownLeft",
    "MouthFrownRight", "MouthDimpleLeft", "MouthDimpleRight", "MouthStretchLeft",
    "MouthStretchRight", "MouthRollLower", "MouthRollUpper", "MouthShrugLower",
    "MouthShrugUpper", "MouthPressLeft", "MouthPressRight", "MouthLowerDownLeft",
    "MouthLowerDownRight", "MouthUpperUpLeft", "MouthUpperUpRight", "BrowDownLeft",
    "BrowDownRight", "BrowInnerUp", "BrowOuterUpLeft", "BrowOuterUpRight", "CheekPuff",
    "CheekSquintLeft", "CheekSquintRight", "NoseSneerLeft", "NoseSneerRight", "TongueOut"
]

def save_debug_data(data, filename):
    """Sauvegarde les données de debug"""
    filepath = DEBUG_DIR / filename
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    logger.info(f"Debug data saved to: {filepath}")

def log_binary_format(data, name="data"):
    """Log le format binaire des données"""
    logger.debug(f"\n=== {name} Binary Format ===")
    logger.debug(f"Total size: {len(data)} bytes")
    logger.debug(f"First 64 bytes (hex): {data[:64].hex()}")
    logger.debug(f"First 32 bytes (raw): {data[:32]}")
    
    # Essayer de décomposer le format
    if len(data) >= 64:
        try:
            # Version LiveLink (4 bytes)
            version = struct.unpack('<I', data[:4])[0]
            logger.debug(f"Version: {version}")
            
            # UUID (36 bytes)
            uuid_bytes = data[4:40]
            uuid_str = uuid_bytes.decode('utf-8', errors='ignore')
            logger.debug(f"UUID: {uuid_str}")
            
            # Analyse plus détaillée
            logger.debug(f"Hex dump (first 256 bytes):")
            for i in range(0, min(256, len(data)), 16):
                hex_str = data[i:i+16].hex()
                ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data[i:i+16])
                logger.debug(f"{i:04x}: {hex_str:<32} {ascii_str}")
        except Exception as e:
            logger.error(f"Error parsing binary format: {e}")

def validate_blendshapes(blendshapes):
    """Valide et analyse les blendshapes"""
    debug_info = {
        "timestamp": datetime.now().isoformat(),
        "type": type(blendshapes).__name__,
        "analysis": {}
    }
    
    if isinstance(blendshapes, list):
        if len(blendshapes) > 0:
            first_element = blendshapes[0]
            
            # Cas 1: Liste de frames (liste de listes)
            if isinstance(first_element, list):
                debug_info["format"] = "list_of_frames"
                debug_info["num_frames"] = len(blendshapes)
                debug_info["values_per_frame"] = len(first_element) if first_element else 0
                
                # Analyse de la première frame
                if first_element:
                    debug_info["first_frame_analysis"] = analyze_frame(first_element)
                    
            # Cas 2: Liste simple de valeurs
            else:
                debug_info["format"] = "single_frame"
                debug_info["num_values"] = len(blendshapes)
                debug_info["frame_analysis"] = analyze_frame(blendshapes)
                
    elif isinstance(blendshapes, np.ndarray):
        debug_info["format"] = "numpy_array"
        debug_info["shape"] = blendshapes.shape
        debug_info["dtype"] = str(blendshapes.dtype)
        
        # Convertir en liste pour analyse
        if blendshapes.ndim == 1:
            debug_info["frame_analysis"] = analyze_frame(blendshapes.tolist())
        elif blendshapes.ndim == 2:
            debug_info["first_frame_analysis"] = analyze_frame(blendshapes[0].tolist())
    
    save_debug_data(debug_info, f"blendshapes_validation_{frame_counter}.json")
    return debug_info

def analyze_frame(values):
    """Analyse une frame de blendshapes"""
    analysis = {
        "num_values": len(values),
        "non_zero_count": sum(1 for v in values if v != 0),
        "min_value": min(values) if values else 0,
        "max_value": max(values) if values else 0,
        "mean_value": np.mean(values) if values else 0,
        "active_blendshapes": {}
    }
    
    # Identifier les blendshapes actifs
    for i, value in enumerate(values):
        if value > 0.01 and i < len(BLENDSHAPE_NAMES):
            analysis["active_blendshapes"][BLENDSHAPE_NAMES[i]] = float(value)
    
    return analysis

def visualize_blendshapes(blendshapes, frame_id):
    """Crée une visualisation des blendshapes"""
    try:
        # Préparer les données
        if isinstance(blendshapes, list):
            if isinstance(blendshapes[0], list):
                values = blendshapes[0]  # Première frame
            else:
                values = blendshapes
        else:
            values = blendshapes
        
        # Limiter aux 52 premiers
        values = values[:52]
        names = BLENDSHAPE_NAMES[:len(values)]
        
        # Créer le graphique
        fig = go.Figure(data=[
            go.Bar(
                x=names,
                y=values,
                text=[f"{v:.3f}" for v in values],
                textposition='auto',
            )
        ])
        
        fig.update_layout(
            title=f"Blendshapes Frame {frame_id}",
            xaxis_title="Blendshape",
            yaxis_title="Value",
            xaxis_tickangle=-45,
            height=600,
            showlegend=False
        )
        
        # Sauvegarder
        filename = f"blendshapes_visualization_{frame_id}.html"
        filepath = DEBUG_DIR / filename
        pio.write_html(fig, filepath)
        logger.info(f"Visualization saved to: {filepath}")
        
        # Créer aussi une image statique avec matplotlib
        plt.figure(figsize=(15, 6))
        plt.bar(range(len(values)), values)
        plt.xticks(range(len(values)), names, rotation=45, ha='right')
        plt.title(f"Blendshapes Frame {frame_id}")
        plt.ylabel("Value")
        plt.tight_layout()
        
        img_filename = f"blendshapes_plot_{frame_id}.png"
        img_filepath = DEBUG_DIR / img_filename
        plt.savefig(img_filepath, dpi=150)
        plt.close()
        logger.info(f"Plot saved to: {img_filepath}")
        
    except Exception as e:
        logger.error(f"Error creating visualization: {e}")

def test_livelink_packet():
    """Test de création d'un paquet LiveLink avec différentes valeurs"""
    global py_face
    
    logger.info("\n=== Test LiveLink Packet Creation ===")
    
    # Test 1: Tous les blendshapes à 0
    py_face.reset()
    data_zero = py_face.encode()
    log_binary_format(data_zero, "All zeros packet")
    
    # Test 2: Seulement JawOpen à 1
    py_face.reset()
    py_face.set_blendshape(FaceBlendShape.JawOpen, 1.0)
    data_jaw = py_face.encode()
    log_binary_format(data_jaw, "JawOpen=1.0 packet")
    
    # Comparer les paquets
    logger.info("\n=== Packet Comparison ===")
    for i in range(min(len(data_zero), len(data_jaw))):
        if data_zero[i] != data_jaw[i]:
            logger.info(f"Byte {i}: {data_zero[i]:02x} -> {data_jaw[i]:02x}")
    
    # Test 3: Valeurs mixtes
    py_face.reset()
    test_values = {
        FaceBlendShape.JawOpen: 0.5,
        FaceBlendShape.EyeBlinkLeft: 0.3,
        FaceBlendShape.EyeBlinkRight: 0.3,
        FaceBlendShape.MouthSmileLeft: 0.7,
        FaceBlendShape.MouthSmileRight: 0.7
    }
    
    for shape, value in test_values.items():
        py_face.set_blendshape(shape, value)
    
    data_mixed = py_face.encode()
    log_binary_format(data_mixed, "Mixed values packet")

def load_neurosync_model():
    """Charge le modèle NeuroSync avec logging détaillé"""
    global blendshape_model
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"🤖 Chargement du modèle NeuroSync sur {device}")
    
    # Info GPU
    if torch.cuda.is_available():
        logger.info(f"GPU disponible: {torch.cuda.get_device_name(0)}")
        logger.info(f"Mémoire GPU: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    
    # Charger le modèle
    model_path = os.path.join(neurosync_path, 'models/neurosync/model/model.pth')
    logger.info(f"Chemin du modèle: {model_path}")
    
    blendshape_model = load_model(model_path, config, device)
    
    # Info sur le modèle
    logger.info("✅ Modèle NeuroSync chargé")
    logger.debug(f"Config: {json.dumps(config, indent=2)}")
    
    return blendshape_model

def init_livelink():
    """Initialise LiveLink avec tests de connexion"""
    global py_face, socket_connection
    
    logger.info(f"🔗 Initialisation LiveLink vers {LIVELINK_IP}:{LIVELINK_PORT}")
    
    py_face = PyLiveLinkFace(name="GalaFace", fps=60)
    logger.info(f"UUID: {py_face.uuid}")
    logger.info(f"Name: {py_face.name}")
    
    socket_connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_connection.connect((LIVELINK_IP, LIVELINK_PORT))
    
    # Test de connexion
    try:
        py_face.reset()
        test_data = py_face.encode()
        socket_connection.sendall(test_data)
        logger.info("✅ Test de connexion LiveLink réussi")
    except Exception as e:
        logger.error(f"❌ Erreur test LiveLink: {e}")
    
    # Tests de paquets
    test_livelink_packet()

def send_to_livelink_with_debug(blendshapes):
    """Envoie les blendshapes avec logging détaillé"""
    global py_face, socket_connection, frame_counter
    
    logger.info(f"\n=== Send to LiveLink - Frame {frame_counter} ===")
    
    if not py_face or not socket_connection:
        logger.error("LiveLink non initialisé")
        return
    
    try:
        # Log les valeurs d'entrée
        logger.debug(f"Input type: {type(blendshapes)}")
        logger.debug(f"Input length: {len(blendshapes) if hasattr(blendshapes, '__len__') else 'N/A'}")
        
        # Reset
        py_face.reset()
        
        # Appliquer les valeurs et logger les actives
        active_count = 0
        active_shapes = {}
        
        for i in range(min(52, len(blendshapes))):
            value = float(blendshapes[i])
            value = max(0.0, min(1.0, value))
            
            if value > 0.01:
                active_count += 1
                shape_name = BLENDSHAPE_NAMES[i] if i < len(BLENDSHAPE_NAMES) else f"Shape_{i}"
                active_shapes[shape_name] = value
                logger.debug(f"  {shape_name}: {value:.3f}")
            
            py_face.set_blendshape(FaceBlendShape(i), value)
        
        logger.info(f"Active blendshapes: {active_count}")
        if active_count > 0:
            logger.info(f"Active values: {active_shapes}")
        
        # Encoder et logger le paquet
        data = py_face.encode()
        logger.debug(f"Encoded packet size: {len(data)} bytes")
        log_binary_format(data, f"Frame {frame_counter} packet")
        
        # Envoyer
        socket_connection.sendall(data)
        logger.info(f"✅ Frame {frame_counter} envoyée")
        
        # Sauvegarder les données de debug
        debug_data = {
            "frame_id": frame_counter,
            "timestamp": datetime.now().isoformat(),
            "input_values": blendshapes[:52] if len(blendshapes) > 52 else blendshapes,
            "active_shapes": active_shapes,
            "packet_size": len(data),
            "packet_hex_preview": data[:64].hex()
        }
        save_debug_data(debug_data, f"frame_{frame_counter}_debug.json")
        
        frame_counter += 1
        
    except Exception as e:
        logger.error(f"❌ Erreur envoi LiveLink: {e}", exc_info=True)

@app.route('/health', methods=['GET'])
def health():
    """Endpoint de santé avec infos détaillées"""
    health_info = {
        "status": "healthy",
        "api_version": "1.0.0 Debug",
        "timestamp": datetime.now().isoformat(),
        "model_loaded": blendshape_model is not None,
        "livelink_connected": socket_connection is not None,
        "debug_dir": str(DEBUG_DIR),
        "frames_sent": frame_counter,
        "config": {
            "port": API_PORT,
            "livelink_ip": LIVELINK_IP,
            "livelink_port": LIVELINK_PORT,
            "gpu_available": torch.cuda.is_available()
        }
    }
    
    if torch.cuda.is_available():
        health_info["gpu_info"] = {
            "device": torch.cuda.get_device_name(0),
            "memory_allocated": f"{torch.cuda.memory_allocated() / 1e9:.2f} GB",
            "memory_cached": f"{torch.cuda.memory_cached() / 1e9:.2f} GB"
        }
    
    return jsonify(health_info)

@app.route('/audio_to_blendshapes', methods=['POST'])
def audio_to_blendshapes_route():
    """Endpoint principal avec debug complet"""
    global frame_counter
    
    request_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    logger.info(f"\n{'='*50}")
    logger.info(f"🎯 NOUVELLE REQUÊTE - ID: {request_id}")
    logger.info(f"{'='*50}")
    
    try:
        # Info requête
        audio_bytes = request.data
        content_type = request.headers.get('Content-Type', 'unknown')
        content_length = len(audio_bytes) if audio_bytes else 0
        
        logger.info(f"📥 Requête reçue:")
        logger.info(f"  - Content-Type: {content_type}")
        logger.info(f"  - Content-Length: {content_length}")
        logger.info(f"  - Headers: {dict(request.headers)}")
        
        if not audio_bytes:
            msg = "No audio data provided."
            logger.error(f"❌ {msg}")
            return jsonify({"status": "error", "message": msg}), 400
        
        # Analyser le format audio
        logger.info(f"🔍 Analyse des données audio:")
        logger.info(f"  - Premiers octets: {audio_bytes[:20]}")
        logger.info(f"  - Type: {type(audio_bytes)}")
        
        # Sauvegarder l'audio pour debug
        audio_file = DEBUG_DIR / f"audio_input_{request_id}.raw"
        with open(audio_file, 'wb') as f:
            f.write(audio_bytes)
        logger.info(f"  - Audio sauvegardé: {audio_file}")
        
        # Traitement des blendshapes
        logger.info(f"🔄 Traitement des blendshapes...")
        start_time = time.time()
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        generated_facial_data = generate_facial_data_from_bytes(
            audio_bytes, 
            blendshape_model, 
            device, 
            config
        )
        
        processing_time = time.time() - start_time
        logger.info(f"⏱️ Temps de traitement: {processing_time:.3f}s")
        
        # Conversion et validation
        if isinstance(generated_facial_data, np.ndarray):
            logger.info(f"📊 Conversion numpy -> liste")
            logger.info(f"  - Shape: {generated_facial_data.shape}")
            logger.info(f"  - Dtype: {generated_facial_data.dtype}")
            blendshapes = generated_facial_data.tolist()
        else:
            blendshapes = generated_facial_data
        
        # Validation approfondie
        logger.info(f"🔍 Validation des blendshapes:")
        validation_info = validate_blendshapes(blendshapes)
        logger.info(f"  - Format: {validation_info.get('format', 'unknown')}")
        
        # Visualisation
        if blendshapes:
            visualize_blendshapes(blendshapes, request_id)
            
            # Envoi à LiveLink avec debug
            if isinstance(blendshapes, list):
                if isinstance(blendshapes[0], list):
                    # Envoyer chaque frame
                    logger.info(f"📤 Envoi de {len(blendshapes)} frames à LiveLink")
                    for i, frame in enumerate(blendshapes[:10]):  # Limiter à 10 pour debug
                        logger.info(f"\n--- Frame {i}/{len(blendshapes)} ---")
                        send_to_livelink_with_debug(frame)
                        time.sleep(0.016)  # ~60 FPS
                else:
                    # Envoyer comme frame unique
                    logger.info(f"📤 Envoi d'une frame unique à LiveLink")
                    send_to_livelink_with_debug(blendshapes)
        
        # Réponse avec méta-données
        result = {
            'blendshapes': blendshapes,
            'debug': {
                'request_id': request_id,
                'processing_time': processing_time,
                'validation': validation_info,
                'frames_sent': frame_counter
            }
        }
        
        logger.info(f"✅ Requête {request_id} terminée avec succès")
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"❌❌❌ ERREUR CRITIQUE: {str(e)}", exc_info=True)
        
        # Sauvegarder l'état d'erreur
        error_data = {
            "request_id": request_id,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "traceback": traceback.format_exc()
        }
        save_debug_data(error_data, f"error_{request_id}.json")
        
        return jsonify({"status": "error", "message": str(e), "request_id": request_id}), 500

@app.route('/debug/test_pattern', methods=['GET'])
def test_pattern():
    """Endpoint de test avec un pattern connu"""
    logger.info("\n=== Test Pattern ===")
    
    # Créer un pattern de test
    test_patterns = [
        # Pattern 1: Ouverture/fermeture bouche
        {
            "name": "jaw_open_close",
            "frames": [
                [0.0] * 17 + [i/10] + [0.0] * 34 for i in range(11)  # JawOpen de 0 à 1
            ]
        },
        # Pattern 2: Clignement
        {
            "name": "blink",
            "frames": [
                [i/5 if j in [0, 7] else 0.0 for j in range(52)] for i in range(6)
            ]
        },
        # Pattern 3: Sourire
        {
            "name": "smile",
            "frames": [
                [0.0] * 23 + [i/10, i/10] + [0.0] * 27 for i in range(11)
            ]
        }
    ]
    
    results = []
    for pattern in test_patterns:
        logger.info(f"Test pattern: {pattern['name']}")
        for i, frame in enumerate(pattern['frames']):
            logger.info(f"  Frame {i}")
            send_to_livelink_with_debug(frame)
            time.sleep(0.1)
        
        results.append({
            "pattern": pattern['name'],
            "frames_sent": len(pattern['frames'])
        })
    
    return jsonify({"test_patterns": results})

@app.route('/debug/report', methods=['GET'])
def debug_report():
    """Génère un rapport de debug complet"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "api_status": {
            "frames_sent": frame_counter,
            "model_loaded": blendshape_model is not None,
            "livelink_connected": socket_connection is not None
        },
        "files_created": []
    }
    
    # Lister les fichiers de debug
    for file in DEBUG_DIR.glob("*"):
        report["files_created"].append({
            "name": file.name,
            "size": file.stat().st_size,
            "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
        })
    
    # Sauvegarder le rapport
    report_file = DEBUG_DIR / f"debug_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Debug report saved to: {report_file}")
    return jsonify(report)

if __name__ == '__main__':
    import traceback
    
    logger.info("\n" + "="*60)
    logger.info("🚀 DÉMARRAGE DE L'API DEBUG AVANCÉ")
    logger.info("="*60)
    
    try:
        # Charger le modèle
        load_neurosync_model()
        
        # Initialiser LiveLink avec tests
        init_livelink()
        
        # Créer des visualisations de test
        logger.info("\n📊 Création des visualisations de test...")
        test_data = [0.0] * 52
        test_data[17] = 0.5  # JawOpen
        test_data[0] = 0.3   # EyeBlinkLeft
        test_data[7] = 0.3   # EyeBlinkRight
        visualize_blendshapes(test_data, "test_startup")
        
        # Lancer l'API
        logger.info(f"\n🌐 API en écoute sur le port {API_PORT}")
        logger.info(f"📁 Logs de debug dans: {DEBUG_DIR}")
        logger.info("="*60 + "\n")
        
        app.run(host='0.0.0.0', port=API_PORT, debug=False)
        
    except Exception as e:
        logger.error(f"❌ Erreur au démarrage: {e}", exc_info=True)
        sys.exit(1)