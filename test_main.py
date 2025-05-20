#!/usr/bin/env python3
"""
Test simple du nouveau main.py
"""

import asyncio
import requests
import time
import numpy as np
import wave
import io

async def test_conversation():
    """Test une conversation simple avec Gala"""
    print("=== Test de conversation Gala v1 ===")
    
    # Vérifier que l'API est en ligne
    try:
        response = requests.get("http://localhost:6969/health")
        if response.status_code == 200:
            print("✓ API en ligne")
            data = response.json()
            print(f"  Version: {data['version']}")
            print(f"  Modèle: {data['model']}")
        else:
            print("✗ L'API ne répond pas")
            return
    except Exception as e:
        print(f"✗ Erreur de connexion à l'API: {e}")
        print("  Lancez d'abord: python api_client.py")
        return
    
    # Créer un audio de test (1 seconde de silence)
    duration = 1.0
    sample_rate = 48000
    num_samples = int(sample_rate * duration)
    audio = np.zeros(num_samples, dtype=np.int16)
    
    # Créer un fichier WAV en mémoire
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio.tobytes())
    
    audio_data = buffer.getvalue()
    
    # Tester l'endpoint blendshapes
    try:
        response = requests.post(
            "http://localhost:6969/audio_to_blendshapes",
            data=audio_data,
            headers={'Content-Type': 'audio/wav'}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✓ Conversion audio → blendshapes réussie")
            print(f"  Nombre de blendshapes: {len(data['blendshapes'])}")
            print(f"  FPS: {data['fps']}")
        else:
            print(f"✗ Erreur de conversion: {response.status_code}")
    except Exception as e:
        print(f"✗ Erreur lors du test: {e}")
    
    print("\n=== Test terminé ===")

if __name__ == "__main__":
    asyncio.run(test_conversation())