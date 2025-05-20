#!/usr/bin/env python3
"""
Script de test pour Gala v1
"""

import numpy as np
import requests
import time

def test_api():
    """Test l'API avec un audio de test"""
    # Générer un son de test (440 Hz, 1 seconde)
    duration = 1.0
    sample_rate = 48000
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.sin(2 * np.pi * 440 * t)
    audio_int16 = (audio * 32767).astype(np.int16)
    
    # Envoyer à l'API
    try:
        response = requests.post(
            'http://localhost:6969/audio_to_blendshapes',
            data=audio_int16.tobytes(),
            headers={'Content-Type': 'audio/wav'}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ API répond correctement")
            print(f"✓ Reçu {len(data['blendshapes'])} blendshapes")
            print(f"✓ Timestamp: {data['timestamp']}")
            print(f"✓ FPS cible: {data['fps']}")
            print(f"\nPremiers 10 blendshapes:")
            for i, (name, value) in enumerate(zip(data['blendshape_names'][:10], data['blendshapes'][:10])):
                print(f"  {name}: {value:.4f}")
        else:
            print(f"✗ Erreur HTTP: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"✗ Erreur de connexion: {e}")
        print("Assurez-vous que l'API est lancée avec: python api_client.py")

if __name__ == "__main__":
    print("=== Test de l'API Gala v1 ===")
    test_api()
