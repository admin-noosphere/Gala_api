#!/usr/bin/env python3
"""
Outil de diagnostic complet pour les blendshapes
Permet de voir exactement ce qui est envoyé à Unreal
"""

import requests
import numpy as np
import json
import time
import struct
import socket

# Configuration
API_URL = "http://localhost:6969"
LIVELINK_IP = "192.168.1.14"
LIVELINK_PORT = 11111

# Noms des blendshapes LiveLink
LIVELINK_NAMES = [
    "EyeBlinkLeft", "EyeLookDownLeft", "EyeLookInLeft", "EyeLookOutLeft", "EyeLookUpLeft",
    "EyeSquintLeft", "EyeWideLeft", "EyeBlinkRight", "EyeLookDownRight", "EyeLookInRight",
    "EyeLookOutRight", "EyeLookUpRight", "EyeSquintRight", "EyeWideRight", 
    "JawForward", "JawLeft", "JawRight", "JawOpen", "MouthClose", "MouthFunnel",
    "MouthPucker", "MouthLeft", "MouthRight", "MouthSmileLeft", "MouthSmileRight",
    "MouthFrownLeft", "MouthFrownRight", "MouthDimpleLeft", "MouthDimpleRight",
    "MouthStretchLeft", "MouthStretchRight", "MouthRollLower", "MouthRollUpper",
    "MouthShrugLower", "MouthShrugUpper", "MouthPressLeft", "MouthPressRight",
    "MouthLowerDownLeft", "MouthLowerDownRight", "MouthUpperUpLeft", "MouthUpperUpRight",
    "BrowDownLeft", "BrowDownRight", "BrowInnerUp", "BrowOuterUpLeft", "BrowOuterUpRight",
    "CheekPuff", "CheekSquintLeft", "CheekSquintRight", "NoseSneerLeft", "NoseSneerRight",
    "TongueOut"
]

def capture_livelink_packet():
    """Capture un paquet LiveLink réel pour analyse"""
    print("\n=== Capture Paquet LiveLink ===")
    
    # Créer un socket d'écoute
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", LIVELINK_PORT))
    sock.settimeout(5.0)
    
    print(f"Écoute sur port {LIVELINK_PORT}...")
    print("Envoyez maintenant un audio à l'API...")
    
    try:
        # Attendre un paquet
        data, addr = sock.recvfrom(4096)
        print(f"Paquet reçu de {addr}: {len(data)} bytes")
        
        # Analyser le paquet
        if len(data) >= 240:  # Taille minimale attendue
            # Décodage basique du header
            version = struct.unpack('<I', data[0:4])[0]
            uuid = data[4:40].decode('utf-8').strip('\x00')
            fps = struct.unpack('<f', data[40:44])[0]
            
            print(f"Version: {version}")
            print(f"UUID: {uuid}")
            print(f"FPS: {fps}")
            
            # Décoder les blendshapes
            offset = 44
            blendshapes = []
            for i in range(52):
                if offset + 4 <= len(data):
                    value = struct.unpack('<f', data[offset:offset+4])[0]
                    blendshapes.append(value)
                    offset += 4
            
            print(f"\nBlendshapes actifs (> 0.1):")
            for i, value in enumerate(blendshapes):
                if value > 0.1:
                    print(f"  [{i:2d}] {LIVELINK_NAMES[i]}: {value:.3f}")
        
    except socket.timeout:
        print("Timeout - aucun paquet reçu")
    except Exception as e:
        print(f"Erreur: {e}")
    finally:
        sock.close()

def test_manual_blendshapes():
    """Envoie des blendshapes manuels pour test"""
    print("\n=== Test Blendshapes Manuels ===")
    
    # Créer des blendshapes de test avec des valeurs connues
    test_sets = [
        {
            "name": "Sourire simple",
            "values": {
                23: 0.7,  # MouthSmileLeft
                24: 0.7   # MouthSmileRight
            }
        },
        {
            "name": "Bouche ouverte",
            "values": {
                17: 0.8,  # JawOpen
                19: 0.3   # MouthFunnel
            }
        },
        {
            "name": "Sourcils levés",
            "values": {
                43: 0.6,  # BrowInnerUp
                44: 0.5,  # BrowOuterUpLeft
                45: 0.5   # BrowOuterUpRight
            }
        },
        {
            "name": "Expression neutre",
            "values": {}  # Tous à 0
        }
    ]
    
    for test_set in test_sets:
        print(f"\nTest: {test_set['name']}")
        
        # Créer les blendshapes
        blendshapes = [0.0] * 52
        for idx, value in test_set['values'].items():
            blendshapes[idx] = value
            print(f"  {LIVELINK_NAMES[idx]}: {value}")
        
        # Envoyer directement via LiveLink
        # (Nécessite d'ajouter un endpoint de test à l'API)
        
        time.sleep(2)

def analyze_real_stream():
    """Analyse un flux réel d'audio Gala"""
    print("\n=== Analyse Flux Réel ===")
    
    # Simuler différents types de voix
    voices = [
        ("Voix masculine grave", 120),
        ("Voix féminine aiguë", 220),
        ("Voix neutre", 170),
        ("Murmure", 100),
        ("Cri", 300)
    ]
    
    for voice_name, frequency in voices:
        print(f"\n{voice_name} ({frequency}Hz):")
        
        # Générer audio
        sample_rate = 16000
        duration = 0.5
        samples = int(sample_rate * duration)
        t = np.linspace(0, duration, samples)
        
        # Voix avec harmoniques
        audio = 0.5 * np.sin(2 * np.pi * frequency * t)
        audio += 0.3 * np.sin(2 * np.pi * frequency * 2 * t)
        audio += 0.1 * np.sin(2 * np.pi * frequency * 3 * t)
        
        # Modulation naturelle
        mod = 0.3 * np.sin(2 * np.pi * 5 * t) + 0.7
        audio *= mod
        
        # Normaliser
        audio = audio / np.max(np.abs(audio))
        audio_int16 = (audio * 16000).astype(np.int16)
        
        # Envoyer à l'API
        response = requests.post(
            f"{API_URL}/audio_to_blendshapes",
            data=audio_int16.tobytes(),
            headers={"Content-Type": "audio/pcm"}
        )
        
        if response.status_code == 200:
            print("  ✓ Traité avec succès")
        else:
            print(f"  ✗ Erreur: {response.status_code}")
        
        time.sleep(1)

def diagnose_mapping_issues():
    """Diagnostique les problèmes de mapping ARKit → LiveLink"""
    print("\n=== Diagnostic Mapping ARKit → LiveLink ===")
    
    # Mappings problématiques courants
    print("\nMappings suspects à vérifier:")
    print("1. Yeux:")
    print("   - ARKit EyeLookIn/Out → LiveLink indices corrects?")
    print("   - ARKit EyeWide → LiveLink EyeWide mapping?")
    
    print("\n2. Bouche:")
    print("   - ARKit MouthLeft/Right → LiveLink orientation?")
    print("   - ARKit MouthPucker → LiveLink MouthPucker?")
    
    print("\n3. Sourcils:")
    print("   - ARKit BrowDown → LiveLink BrowDown inversion?")
    print("   - ARKit BrowOuter → LiveLink séparation gauche/droite?")
    
    print("\n4. Joues:")
    print("   - ARKit CheekPuff → LiveLink CheekPuff échelle?")
    print("   - ARKit CheekSquint → LiveLink synchronisation?")

def suggest_calibration():
    """Suggère une calibration pour corriger les expressions"""
    print("\n=== Suggestions de Calibration ===")
    
    print("\n1. Créer un set de calibration:")
    print("   - Enregistrer des expressions de référence")
    print("   - Noter les valeurs attendues vs obtenues")
    print("   - Ajuster les mappings en conséquence")
    
    print("\n2. Facteurs de correction suggérés:")
    corrections = {
        "JawOpen": {"scale": 0.7, "offset": 0.0},
        "MouthSmile": {"scale": 1.2, "offset": -0.1},
        "BrowInnerUp": {"scale": 0.8, "offset": 0.0},
        "EyeWide": {"scale": 0.5, "offset": 0.0}
    }
    
    for shape, params in corrections.items():
        print(f"   {shape}: scale={params['scale']}, offset={params['offset']}")
    
    print("\n3. Tester avec différents profils:")
    print("   - Voix masculine")
    print("   - Voix féminine")
    print("   - Voix d'enfant")
    print("   - Murmure vs cri")

def main():
    """Programme principal"""
    print("=== Diagnostic Complet Blendshapes ===")
    print(f"API: {API_URL}")
    print(f"LiveLink: {LIVELINK_IP}:{LIVELINK_PORT}")
    print()
    
    # Vérifier l'API
    try:
        response = requests.get(f"{API_URL}/health")
        health = response.json()
        print(f"API Status: {health['status']}")
        print(f"GPU: {health.get('gpu', 'N/A')}")
        print()
    except:
        print("⚠️  API non accessible")
        return
    
    # Tests
    tests = [
        ("Blendshapes Manuels", test_manual_blendshapes),
        ("Analyse Flux Réel", analyze_real_stream),
        ("Diagnostic Mapping", diagnose_mapping_issues),
        ("Suggestions Calibration", suggest_calibration),
        # ("Capture LiveLink", capture_livelink_packet)  # Commenté car conflits de port
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Test: {test_name}")
        print('='*60)
        
        try:
            test_func()
        except Exception as e:
            print(f"Erreur: {e}")
        
        time.sleep(1)
    
    print("\n=== Diagnostic Terminé ===")
    print("\nProchaines étapes:")
    print("1. Vérifier les logs dans Unreal Engine")
    print("2. Enregistrer les blendshapes réels vs attendus")
    print("3. Ajuster les mappings si nécessaire")
    print("4. Tester avec l'animation idle pour comparaison")

if __name__ == "__main__":
    main()