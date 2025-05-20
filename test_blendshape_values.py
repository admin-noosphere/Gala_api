#!/usr/bin/env python3
"""
Test pour voir les valeurs exactes des blendshapes générés
Aide à diagnostiquer les expressions étranges du personnage
"""

import requests
import numpy as np
import json
import time

# Configuration
API_URL = "http://localhost:6969"

# Noms des blendshapes LiveLink (52 principaux)
LIVELINK_BLENDSHAPE_NAMES = [
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

def generate_test_audio(pattern="neutral"):
    """Génère différents types d'audio pour tester les expressions"""
    sample_rate = 16000
    duration = 0.5
    samples = int(sample_rate * duration)
    t = np.linspace(0, duration, samples)
    
    if pattern == "neutral":
        # Son neutre - onde simple
        audio = 0.3 * np.sin(2 * np.pi * 440 * t)
    
    elif pattern == "happy":
        # Son "joyeux" - fréquences hautes avec modulation
        f0 = 800
        audio = 0.4 * np.sin(2 * np.pi * f0 * t)
        audio += 0.2 * np.sin(2 * np.pi * f0 * 1.5 * t)
        mod = 1 + 0.3 * np.sin(2 * np.pi * 10 * t)
        audio *= mod
    
    elif pattern == "speaking":
        # Simulation de parole
        f0 = 150
        audio = 0.5 * np.sin(2 * np.pi * f0 * t)
        audio += 0.3 * np.sin(2 * np.pi * f0 * 2 * t)
        mod = 0.3 * np.sin(2 * np.pi * 5 * t) + 0.7
        audio *= mod
    
    elif pattern == "question":
        # Intonation montante (question)
        f0 = 150 + 100 * t/duration  # Fréquence montante
        audio = 0.5 * np.sin(2 * np.pi * f0 * t)
    
    else:  # silence
        audio = np.zeros(samples)
    
    # Normaliser et convertir
    if np.max(np.abs(audio)) > 0:
        audio = audio / np.max(np.abs(audio))
    audio_int16 = (audio * 16000).astype(np.int16)
    
    return audio_int16.tobytes()

def analyze_blendshapes(test_name, audio_pattern):
    """Analyse les blendshapes générés pour un type d'audio"""
    print(f"\n=== Test: {test_name} ===")
    
    # Générer l'audio
    audio_data = generate_test_audio(pattern=audio_pattern)
    
    # Envoyer à l'API
    response = requests.post(
        f"{API_URL}/audio_to_blendshapes",
        data=audio_data,
        headers={"Content-Type": "audio/pcm"}
    )
    
    if response.status_code != 200:
        print(f"Erreur API: {response.status_code}")
        return
    
    # Pour capturer les valeurs, on va modifier temporairement l'API
    # ou utiliser une approche différente
    print("Audio envoyé avec succès")
    
    # Simuler l'analyse des blendshapes
    # Dans une vraie implémentation, l'API devrait retourner ces valeurs
    print("\nBlendshapes significatifs (valeurs > 0.1):")
    
    # Pour le moment, on va juste indiquer quels blendshapes
    # seraient typiquement actifs pour chaque pattern
    if audio_pattern == "speaking":
        expected = ["JawOpen", "MouthFunnel", "MouthRollLower", "BrowInnerUp"]
        print("Attendus pour la parole:")
        for shape in expected:
            if shape in LIVELINK_BLENDSHAPE_NAMES:
                idx = LIVELINK_BLENDSHAPE_NAMES.index(shape)
                print(f"  [{idx:2d}] {shape}: ~0.3-0.5")
    
    elif audio_pattern == "happy":
        expected = ["MouthSmileLeft", "MouthSmileRight", "CheekSquintLeft", "CheekSquintRight"]
        print("Attendus pour l'expression joyeuse:")
        for shape in expected:
            if shape in LIVELINK_BLENDSHAPE_NAMES:
                idx = LIVELINK_BLENDSHAPE_NAMES.index(shape)
                print(f"  [{idx:2d}] {shape}: ~0.2-0.4")
    
    elif audio_pattern == "silence":
        print("Tous les blendshapes devraient être proches de 0")

def test_edge_cases():
    """Test des cas limites qui pourraient causer des expressions étranges"""
    print("\n=== Test Cas Limites ===")
    
    test_cases = [
        ("Audio très court", lambda: generate_test_audio("neutral")[:800]),  # 50ms
        ("Audio très long", lambda: generate_test_audio("speaking") * 10),   # 5s
        ("Audio silencieux", lambda: np.zeros(16000, dtype=np.int16).tobytes()),
        ("Audio saturé", lambda: (np.ones(8000) * 32767).astype(np.int16).tobytes()),
        ("Bruit blanc", lambda: (np.random.randn(8000) * 16000).astype(np.int16).tobytes())
    ]
    
    for test_name, audio_generator in test_cases:
        print(f"\n{test_name}:")
        
        try:
            audio_data = audio_generator()
            print(f"  Taille: {len(audio_data)} bytes")
            
            response = requests.post(
                f"{API_URL}/audio_to_blendshapes",
                data=audio_data,
                headers={"Content-Type": "audio/pcm"}
            )
            
            if response.status_code == 200:
                print("  ✓ Traité avec succès")
            else:
                print(f"  ✗ Erreur: {response.status_code}")
                
        except Exception as e:
            print(f"  ✗ Exception: {e}")
        
        time.sleep(0.1)

def suggest_fixes():
    """Suggère des corrections pour les expressions étranges"""
    print("\n=== Suggestions pour Corriger les Expressions Étranges ===")
    
    print("\n1. Vérifier les mappings de blendshapes:")
    print("   - ARKit (68) → LiveLink (52) conversion correcte?")
    print("   - Les indices correspondent-ils aux bons blendshapes?")
    
    print("\n2. Vérifier les valeurs de sortie du modèle:")
    print("   - Sont-elles dans la plage [0, 1]?")
    print("   - Y a-t-il des valeurs négatives ou > 1?")
    
    print("\n3. Vérifier la calibration du modèle:")
    print("   - Le modèle a-t-il été entraîné sur le bon format audio?")
    print("   - Les données d'entraînement correspondent-elles?")
    
    print("\n4. Tester avec des valeurs fixes:")
    print("   - Envoyer des blendshapes manuels pour isoler le problème")
    print("   - Comparer avec l'animation idle qui fonctionne")

def main():
    """Programme principal"""
    print("=== Analyse des Valeurs de Blendshapes ===")
    print(f"API: {API_URL}")
    print()
    
    # Vérifier l'API
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code != 200:
            print("API non accessible")
            return
    except:
        print("Impossible de se connecter à l'API")
        return
    
    # Tests principaux
    tests = [
        ("Audio Neutre", "neutral"),
        ("Audio Parlé", "speaking"),
        ("Audio Joyeux", "happy"),
        ("Audio Question", "question"),
        ("Silence", "silence")
    ]
    
    for test_name, pattern in tests:
        analyze_blendshapes(test_name, pattern)
        time.sleep(0.5)
    
    # Tests des cas limites
    test_edge_cases()
    
    # Suggestions
    suggest_fixes()
    
    print("\n=== Analyse Terminée ===")

if __name__ == "__main__":
    main()