#!/usr/bin/env python3
"""
Test de l'API avec gestion audio fixée
Teste spécifiquement l'envoi de données PCM brutes
"""

import requests
import numpy as np
import time
import io

# Configuration
API_URL = "http://localhost:6969"
SAMPLE_RATE = 16000  # Le format expected par Gala

def generate_pcm_audio(duration=1.0, frequency=440):
    """Génère des données PCM brutes (ce que Gala envoie)"""
    samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, samples)
    audio = np.sin(2 * np.pi * frequency * t)
    
    # Convertir en int16 PCM
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

def test_pcm_to_blendshapes():
    """Test avec données PCM brutes"""
    print("\n=== Test PCM to Blendshapes ===")
    
    # Générer audio PCM brut
    print("Génération de données PCM brutes...")
    pcm_data = generate_pcm_audio(duration=0.5)
    print(f"Taille des données PCM: {len(pcm_data)} bytes")
    
    try:
        # Envoyer à l'API sans headers WAV
        print("Envoi des données PCM à l'API...")
        response = requests.post(
            f"{API_URL}/audio_to_blendshapes",
            data=pcm_data,
            headers={"Content-Type": "audio/pcm"}  # Indique explicitement PCM
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Réponse: {data}")
            print("✓ Test réussi - l'API gère correctement le PCM")
            return True
        else:
            try:
                error_data = response.json()
                print(f"Erreur: {error_data}")
            except:
                print(f"Erreur: {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception: {e}")
        return False

def test_multiple_pcm_chunks():
    """Test avec plusieurs chunks PCM successifs"""
    print("\n=== Test Multiple PCM Chunks ===")
    
    chunk_duration = 0.1  # 100ms chunks
    
    try:
        for i in range(5):
            # Générer un chunk PCM
            frequency = 440 + i * 100  # Varie la fréquence
            pcm_chunk = generate_pcm_audio(duration=chunk_duration, frequency=frequency)
            
            print(f"\nChunk {i+1}: freq={frequency}Hz, size={len(pcm_chunk)} bytes")
            
            response = requests.post(
                f"{API_URL}/audio_to_blendshapes",
                data=pcm_chunk,
                headers={"Content-Type": "audio/pcm"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Chunk {i+1} traité avec succès")
            else:
                print(f"✗ Erreur chunk {i+1}: {response.status_code}")
                try:
                    print(f"   Détails: {response.json()}")
                except:
                    print(f"   Détails: {response.text}")
            
            time.sleep(0.1)  # Attendre entre les chunks
        
        return True
        
    except Exception as e:
        print(f"Exception: {e}")
        return False

def main():
    """Programme principal"""
    print("=== Test API Fixed Audio ===")
    print(f"URL API: {API_URL}")
    print(f"Format: PCM brut 16kHz 16-bit mono")
    print()
    
    # Vérifier que l'API est prête
    print("Vérification de l'API...")
    if not test_health():
        print("L'API n'est pas accessible")
        return
    
    # Tests
    tests = [
        ("PCM to Blendshapes", test_pcm_to_blendshapes),
        ("Multiple PCM Chunks", test_multiple_pcm_chunks)
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Test: {test_name}")
        print('='*50)
        
        if test_func():
            print(f"\n✓ {test_name} réussi")
        else:
            print(f"\n✗ {test_name} échoué")
        
        time.sleep(1)
    
    print("\n=== Tests terminés ===")

if __name__ == "__main__":
    main()