#!/usr/bin/env python3
"""
Script de test pour vérifier la connexion LiveLink avec Unreal Engine
Envoie des blendshapes neutres (idle) en boucle
Format compatible avec NeuroSync_Player
"""

import time
import socket
import struct
import numpy as np
import datetime
import uuid
from typing import List, Dict

# Configuration
LIVELINK_HOST = "192.168.1.14"  # IP d'Unreal Engine
LIVELINK_PORT = 11111
FPS = 60

# Noms des 68 blendshapes ARKit
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

class PyLiveLinkFace:
    """Implémentation simplifiée de PyLiveLinkFace pour le test"""
    
    def __init__(self, name: str = "GalaFace", fps: int = 60):
        self.name = name
        self.fps = fps
        self.uuid = str(uuid.uuid1())
        self._version = 6
        self._blend_shapes = [0.0] * 61  # Format LiveLink: 61 valeurs
    
    def set_blendshape(self, index: int, value: float):
        """Définit la valeur d'un blendshape (0-60)"""
        if 0 <= index < 61:
            self._blend_shapes[index] = max(0.0, min(1.0, value))
    
    def encode(self) -> bytes:
        """Encode les données au format LiveLink"""
        # Version
        version_packed = struct.pack('<I', self._version)
        
        # UUID
        uuid_packed = self.uuid.encode('utf-8')
        
        # Nom
        name_bytes = self.name.encode('utf-8')
        name_length_packed = struct.pack('!i', len(name_bytes))
        
        # Timestamp
        now = datetime.datetime.now()
        total_seconds = (now.hour * 3600 + now.minute * 60 + 
                        now.second + now.microsecond / 1000000.0)
        frames = int(total_seconds * self.fps)
        sub_frame = int((total_seconds * self.fps - frames) * 4294967296)
        frames_packed = struct.pack("!II", frames, sub_frame)
        
        # Framerate
        frame_rate_packed = struct.pack("!II", self.fps, 1)
        
        # Blendshapes
        data_packed = struct.pack('!B', 61)  # Nombre de blendshapes
        data_packed += struct.pack('!61f', *self._blend_shapes)
        
        return (version_packed + uuid_packed + name_length_packed + 
                name_bytes + frames_packed + frame_rate_packed + data_packed)

def create_idle_animation(frame_index: int, total_frames: int = 120) -> List[float]:
    """
    Crée une animation idle simple avec respiration et clignements
    
    Args:
        frame_index: Index de la frame actuelle
        total_frames: Nombre total de frames dans le cycle
        
    Returns:
        Liste de 61 valeurs float pour les blendshapes
    """
    # Initialiser tous les blendshapes à 0
    blendshapes = [0.0] * 61
    
    # Animation de respiration subtile (JawOpen)
    breathing_phase = (frame_index / total_frames) * 2 * np.pi
    jaw_value = 0.05 * np.sin(breathing_phase)  # Valeur entre -0.05 et 0.05
    blendshapes[17] = max(0, jaw_value)  # JawOpen (index 17)
    
    # Clignements périodiques
    blink_cycle = 240  # Cligner toutes les 4 secondes à 60 FPS
    blink_duration = 6  # Durée du clignement en frames
    
    if (frame_index % blink_cycle) < blink_duration:
        blink_value = np.sin((frame_index % blink_cycle) / blink_duration * np.pi)
        blendshapes[0] = blink_value  # EyeBlinkLeft
        blendshapes[7] = blink_value  # EyeBlinkRight
    
    # Micro-mouvements des sourcils
    brow_phase = (frame_index / (total_frames * 2)) * 2 * np.pi
    brow_value = 0.02 * np.sin(brow_phase)
    blendshapes[43] = max(0, brow_value)  # BrowInnerUp
    
    # Léger sourire occasionnel
    smile_cycle = 300  # Toutes les 5 secondes
    if (frame_index % smile_cycle) < 60:  # Sourire pendant 1 seconde
        smile_value = 0.1 * np.sin((frame_index % smile_cycle) / 60 * np.pi)
        blendshapes[23] = smile_value  # MouthSmileLeft
        blendshapes[24] = smile_value  # MouthSmileRight
    
    return blendshapes

def test_udp_connection():
    """Test simple de connexion UDP"""
    print(f"Test de connexion UDP vers {LIVELINK_HOST}:{LIVELINK_PORT}")
    
    py_face = PyLiveLinkFace(name="GalaFace")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        # Créer un paquet de test avec des valeurs neutres
        packet = py_face.encode()
        sock.connect((LIVELINK_HOST, LIVELINK_PORT))
        sock.sendall(packet)
        print("✓ Paquet de test envoyé avec succès")
        return True
    except Exception as e:
        print(f"✗ Erreur lors de l'envoi: {e}")
        return False
    finally:
        sock.close()

def main():
    """
    Boucle principale: envoie une animation idle à Unreal Engine
    """
    print("=== Test de connexion LiveLink (Compatible NeuroSync) ===")
    print(f"Cible: {LIVELINK_HOST}:{LIVELINK_PORT}")
    print(f"FPS: {FPS}")
    print()
    
    # Test initial de connexion
    if not test_udp_connection():
        print("Impossible de se connecter. Vérifiez l'IP et le port.")
        return
    
    print("\nDémarrage de l'animation idle...")
    print("Appuyez sur Ctrl+C pour arrêter")
    
    # Créer l'objet PyLiveLinkFace
    py_face = PyLiveLinkFace(name="GalaFace")
    
    # Créer le socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect((LIVELINK_HOST, LIVELINK_PORT))
    
    frame_index = 0
    frame_time = 1.0 / FPS
    
    try:
        while True:
            start_time = time.time()
            
            # Créer les blendshapes pour cette frame
            blendshapes = create_idle_animation(frame_index)
            
            # Appliquer les valeurs
            for i, value in enumerate(blendshapes):
                py_face.set_blendshape(i, value)
            
            # Encoder et envoyer
            packet = py_face.encode()
            sock.sendall(packet)
            
            # Afficher des informations toutes les secondes
            if frame_index % FPS == 0:
                print(f"Frame {frame_index}: Envoi idle animation...")
                # Afficher quelques valeurs pour debug
                print(f"  JawOpen: {blendshapes[17]:.3f}")
                print(f"  EyeBlink_L: {blendshapes[0]:.3f}")
                print(f"  MouthSmile_L: {blendshapes[23]:.3f}")
            
            # Incrémenter l'index de frame
            frame_index = (frame_index + 1) % (FPS * 10)  # Cycle de 10 secondes
            
            # Maintenir le FPS
            elapsed = time.time() - start_time
            if elapsed < frame_time:
                time.sleep(frame_time - elapsed)
                
    except KeyboardInterrupt:
        print("\n\nArrêt de l'animation...")
    finally:
        sock.close()
        print("Connexion fermée.")

if __name__ == "__main__":
    main() 