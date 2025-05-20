#!/usr/bin/env python3
"""
Test de l'API avec envoi LiveLink
Vérifie que l'audio est correctement converti et envoyé à Unreal
"""

import requests
import numpy as np
import json
import time
import wave
import struct

# Configuration
API_URL = "http://localhost:6969"
SAMPLE_RATE = 48000


def generate_test_audio(duration=1.0, frequency=440):
    """Génère un son de test (sinusoïde)"""
    samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, samples)
    audio = np.sin(2 * np.pi * frequency * t)
    
    # Convertir en int16
    audio_int16 = (audio * 32767).astype(np.int16)
    return audio_int16.tobytes()


def test_health():
    """Test de l'endpoint health"""
    print("=== Test Health ===")
    try:
        response = requests.get(f"{API_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Erreur: {e}")
        return False


def test_audio_to_blendshapes():
    """Test de conversion audio -> blendshapes"""
    print("\n=== Test Audio to Blendshapes ===")
    
    # Générer audio de test
    audio_data = generate_test_audio(duration=0.5)
    
    try:
        # Envoyer à l'API
        response = requests.post(
            f"{API_URL}/audio_to_blendshapes",
            data=audio_data,
            headers={"Content-Type": "audio/wav"}
        )
        
        print(f"Status: {response.status_code}")
        data = response.json()
        
        if "blendshapes" in data:
            blendshapes = data["blendshapes"]
            print(f"Nombre de blendshapes: {len(blendshapes)}")
            
            # Afficher quelques valeurs non-nulles
            non_zero = [(i, val) for i, val in enumerate(blendshapes) if val > 0.01]
            print(f"Blendshapes actifs: {len(non_zero)}")
            for idx, val in non_zero[:5]:
                name = data["blendshape_names"][idx] if "blendshape_names" in data else f"Shape{idx}"
                print(f"  {name}: {val:.3f}")
            
            print(f"LiveLink envoyé: {data.get('sent_to_livelink', False)}")
            return True
        else:
            print(f"Erreur: {data}")
            return False
            
    except Exception as e:
        print(f"Erreur: {e}")
        return False


def test_stream_audio():
    """Test du streaming audio"""
    print("\n=== Test Stream Audio ===")
    
    # Envoyer plusieurs petits chunks
    chunk_duration = 0.05  # 50ms
    
    try:
        for i in range(10):
            # Générer un petit chunk audio
            audio_chunk = generate_test_audio(duration=chunk_duration, frequency=440 + i*50)
            
            response = requests.post(
                f"{API_URL}/stream_audio",
                data=audio_chunk,
                headers={"Content-Type": "audio/wav"}
            )
            
            data = response.json()
            print(f"Chunk {i}: {data['status']}")
            
            if data['status'] == 'sent_to_livelink':
                print(f"  Blendshapes envoyés: {data['blendshapes_count']}")
            elif data['status'] == 'buffering':
                print(f"  Buffer: {data['buffer_ms']:.0f}ms")
            
            time.sleep(0.05)
        
        return True
        
    except Exception as e:
        print(f"Erreur: {e}")
        return False


def test_continuous_stream():
    """Test de stream continu avec animation"""
    print("\n=== Test Stream Continu (5 secondes) ===")
    
    try:
        start_time = time.time()
        duration = 5.0
        
        while time.time() - start_time < duration:
            # Générer audio avec fréquence variable (pour animer la bouche)
            t = time.time() - start_time
            frequency = 440 + 200 * np.sin(t)  # Fréquence oscillante
            
            audio_chunk = generate_test_audio(duration=0.1, frequency=frequency)
            
            response = requests.post(
                f"{API_URL}/audio_to_blendshapes",
                data=audio_chunk,
                headers={"Content-Type": "audio/wav"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if "blendshapes" in data:
                    # Afficher l'état de la bouche
                    jaw_open = data["blendshapes"][17]  # JawOpen
                    print(f"Temps: {t:.1f}s - JawOpen: {jaw_open:.3f} - Freq: {frequency:.0f}Hz")
            
            time.sleep(0.033)  # ~30 FPS
        
        print("Stream terminé")
        return True
        
    except Exception as e:
        print(f"Erreur: {e}")
        return False


def main():
    """Programme principal"""
    print("=== Test API NeuroSync avec LiveLink ===")
    print(f"URL API: {API_URL}")
    print()
    
    # Attendre que l'API soit prête
    print("Vérification de l'API...")
    for i in range(5):
        if test_health():
            break
        print(f"Tentative {i+1}/5...")
        time.sleep(1)
    else:
        print("L'API n'est pas accessible")
        return
    
    # Tests
    tests = [
        ("Audio to Blendshapes", test_audio_to_blendshapes),
        ("Stream Audio", test_stream_audio),
        ("Stream Continu", test_continuous_stream)
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Test: {test_name}")
        print('='*50)
        
        if test_func():
            print(f"✓ {test_name} réussi")
        else:
            print(f"✗ {test_name} échoué")
        
        time.sleep(1)
    
    print("\n=== Tests terminés ===")


if __name__ == "__main__":
    main()