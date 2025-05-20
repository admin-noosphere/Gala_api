#!/usr/bin/env python3
"""
Test différentes variations d'animations idle pour vérifier
ce qui est visible dans Unreal Engine
"""

import time
import socket
import struct
import numpy as np
from typing import List

# Configuration
LIVELINK_HOST = "192.168.1.14"  # IP d'Unreal Engine LiveLink
LIVELINK_PORT = 11111
FPS = 60

# Noms des blendshapes pour référence
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

def create_udp_packet(blendshapes: List[float], subject_name: str = "GalaTest") -> bytes:
    """Crée un paquet UDP LiveLink"""
    packet = b''
    packet += b'LIVE'
    
    subject_bytes = subject_name.encode('utf-8')
    packet += struct.pack('I', len(subject_bytes))
    packet += subject_bytes
    
    packet += struct.pack('d', time.time())
    packet += struct.pack('I', len(blendshapes))
    
    for value in blendshapes:
        packet += struct.pack('f', value)
    
    return packet

def test_neutral():
    """Test 1: Position neutre (toutes valeurs à 0)"""
    print("\n=== Test 1: Position Neutre ===")
    blendshapes = [0.0] * 68
    return blendshapes

def test_eyes_only():
    """Test 2: Animation des yeux uniquement"""
    print("\n=== Test 2: Yeux seulement ===")
    blendshapes = [0.0] * 68
    
    # Clignement
    blendshapes[0] = 1.0  # EyeBlink_L
    blendshapes[1] = 1.0  # EyeBlink_R
    
    return blendshapes

def test_mouth_only():
    """Test 3: Animation de la bouche uniquement"""
    print("\n=== Test 3: Bouche seulement ===")
    blendshapes = [0.0] * 68
    
    # Ouverture de la bouche
    blendshapes[17] = 0.5  # JawOpen
    blendshapes[23] = 0.3  # MouthSmile_L
    blendshapes[24] = 0.3  # MouthSmile_R
    
    return blendshapes

def test_eyebrows_only():
    """Test 4: Animation des sourcils uniquement"""
    print("\n=== Test 4: Sourcils seulement ===")
    blendshapes = [0.0] * 68
    
    # Lever les sourcils
    blendshapes[44] = 0.7  # BrowInnerUp
    blendshapes[45] = 0.5  # BrowOuterUp_L
    blendshapes[46] = 0.5  # BrowOuterUp_R
    
    return blendshapes

def test_breathing():
    """Test 5: Animation de respiration"""
    print("\n=== Test 5: Respiration ===")
    blendshapes = [0.0] * 68
    
    # Respiration subtile
    phase = time.time() * 0.5
    breathing = 0.1 * np.sin(phase)
    
    blendshapes[17] = max(0, breathing)  # JawOpen
    blendshapes[46] = max(0, breathing * 0.5)  # CheekPuff
    blendshapes[49] = max(0, breathing * 0.3)  # NoseSneer_L
    blendshapes[50] = max(0, breathing * 0.3)  # NoseSneer_R
    
    return blendshapes

def test_full_expression(expression_type: str):
    """Test 6: Expressions complètes"""
    print(f"\n=== Test 6: Expression {expression_type} ===")
    blendshapes = [0.0] * 68
    
    if expression_type == "happy":
        blendshapes[23] = 0.8  # MouthSmile_L
        blendshapes[24] = 0.8  # MouthSmile_R
        blendshapes[47] = 0.5  # CheekSquint_L
        blendshapes[48] = 0.5  # CheekSquint_R
        blendshapes[10] = 0.3  # EyeSquint_L
        blendshapes[11] = 0.3  # EyeSquint_R
        
    elif expression_type == "sad":
        blendshapes[25] = 0.7  # MouthFrown_L
        blendshapes[26] = 0.7  # MouthFrown_R
        blendshapes[42] = 0.5  # BrowDown_L
        blendshapes[43] = 0.5  # BrowDown_R
        blendshapes[44] = 0.3  # BrowInnerUp
        
    elif expression_type == "surprised":
        blendshapes[17] = 0.6  # JawOpen
        blendshapes[12] = 0.8  # EyeWide_L
        blendshapes[13] = 0.8  # EyeWide_R
        blendshapes[45] = 0.7  # BrowOuterUp_L
        blendshapes[46] = 0.7  # BrowOuterUp_R
        blendshapes[44] = 0.8  # BrowInnerUp
    
    return blendshapes

def main():
    """Programme principal de test"""
    print("=== Test des variations d'animation idle ===")
    print(f"Cible: {LIVELINK_HOST}:{LIVELINK_PORT}")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    tests = [
        ("Neutre", test_neutral),
        ("Yeux", test_eyes_only),
        ("Bouche", test_mouth_only),
        ("Sourcils", test_eyebrows_only),
        ("Respiration", test_breathing),
        ("Joie", lambda: test_full_expression("happy")),
        ("Tristesse", lambda: test_full_expression("sad")),
        ("Surprise", lambda: test_full_expression("surprised")),
    ]
    
    try:
        for test_name, test_func in tests:
            print(f"\n--- Exécution: {test_name} ---")
            print("Durée: 3 secondes")
            
            start_time = time.time()
            while time.time() - start_time < 3:
                # Créer les blendshapes pour ce test
                blendshapes = test_func()
                
                # Créer et envoyer le paquet
                packet = create_udp_packet(blendshapes)
                sock.sendto(packet, (LIVELINK_HOST, LIVELINK_PORT))
                
                # Afficher quelques valeurs importantes
                if int(time.time() - start_time) % 1 == 0:
                    active_shapes = [(BLENDSHAPE_NAMES[i], v) 
                                   for i, v in enumerate(blendshapes) 
                                   if v > 0.01]
                    if active_shapes:
                        print("Blendshapes actives:")
                        for name, value in active_shapes[:5]:  # Top 5
                            print(f"  {name}: {value:.3f}")
                
                time.sleep(1/FPS)
            
            print(f"✓ Test {test_name} terminé")
            
            # Pause entre les tests
            print("\nPause de 2 secondes...")
            time.sleep(2)
    
    except KeyboardInterrupt:
        print("\n\nTests interrompus")
    finally:
        sock.close()
        print("Connexion fermée.")

if __name__ == "__main__":
    main()