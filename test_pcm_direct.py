#!/usr/bin/env python3
"""
Test du traitement PCM direct
"""

import requests
import numpy as np
import time

# Configuration
API_URL = "http://localhost:6969"
SAMPLE_RATE = 16000

def generate_pcm_test_audio(duration=0.5, frequency=440):
    """Génère un audio PCM de test"""
    samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, samples)
    
    # Onde sinusoïdale simple
    audio = np.sin(2 * np.pi * frequency * t)
    
    # Convertir en PCM 16-bit
    audio_int16 = (audio * 16000).astype(np.int16)
    
    return audio_int16.tobytes()

def test_health():
    """Test de santé de l'API"""
    print("=== Test Health ===")
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            health = response.json()
            print(f"Status: {health['status']}")
            print(f"Model loaded: {health['model_loaded']}")
            print(f"LiveLink connected: {health['livelink_connected']}")
            print(f"Sample rate: {health['sample_rate']}Hz")
            print(f"Buffer: {health['buffer_level']}/{health['buffer_max']} bytes")
            return True
    except Exception as e:
        print(f"Erreur: {e}")
        return False

def test_direct_pcm():
    """Test du traitement PCM direct"""
    print("\n=== Test PCM Direct ===")
    
    # Générer un audio de test
    test_audio = generate_pcm_test_audio(duration=0.5)
    print(f"Audio généré: {len(test_audio)} bytes")
    
    try:
        # Tester le traitement direct
        response = requests.post(
            f"{API_URL}/test_direct_pcm",
            data=test_audio,
            headers={'Content-Type': 'audio/pcm'}
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Résultat: {data}")
            return True
        else:
            print(f"Erreur: {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception: {e}")
        return False

def test_buffer_system():
    """Test du système de buffer"""
    print("\n=== Test Buffer System ===")
    
    # Envoyer plusieurs petits chunks
    chunk_size = 1024
    total_duration = 1.0
    
    # Générer un audio complet
    full_audio = generate_pcm_test_audio(duration=total_duration)
    
    print(f"Audio total: {len(full_audio)} bytes")
    print(f"Taille des chunks: {chunk_size} bytes")
    
    chunks_sent = 0
    for i in range(0, len(full_audio), chunk_size):
        chunk = full_audio[i:i + chunk_size]
        
        try:
            response = requests.post(
                f"{API_URL}/audio_to_blendshapes",
                data=chunk,
                headers={'Content-Type': 'audio/pcm'}
            )
            
            if response.status_code == 200:
                chunks_sent += 1
                if chunks_sent % 5 == 0:
                    data = response.json()
                    print(f"Chunk {chunks_sent}: Buffer {data['buffer_level']} bytes")
            else:
                print(f"Erreur chunk {chunks_sent}: {response.status_code}")
                
        except Exception as e:
            print(f"Exception: {e}")
            break
        
        time.sleep(0.02)  # Petit délai entre chunks
    
    print(f"\nTotal chunks envoyés: {chunks_sent}")
    
    # Flush le buffer
    try:
        response = requests.post(f"{API_URL}/flush_buffer")
        print("Buffer flush demandé")
    except:
        pass
    
    return chunks_sent > 0

def test_realistic_speech():
    """Test avec audio ressemblant à de la parole"""
    print("\n=== Test Audio Parole ===")
    
    # Générer un audio qui ressemble à de la parole
    duration = 2.0
    samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, samples)
    
    # Fréquence fondamentale variable (voix)
    f0 = 150 + 50 * np.sin(2 * np.pi * 1 * t)  # Variation lente
    
    # Signal avec harmoniques
    audio = 0.0
    for harmonic in range(1, 4):
        audio += (1.0 / harmonic) * np.sin(2 * np.pi * f0 * harmonic * t)
    
    # Modulation d'amplitude (rythme de parole)
    envelope = 0.7 + 0.3 * np.sin(2 * np.pi * 3 * t)
    audio *= envelope
    
    # Normaliser et convertir
    audio = audio / np.max(np.abs(audio))
    audio_int16 = (audio * 16000).astype(np.int16)
    
    print(f"Audio généré: {len(audio_int16.tobytes())} bytes")
    
    # Envoyer par chunks
    chunk_duration = 0.05  # 50ms
    chunk_samples = int(SAMPLE_RATE * chunk_duration)
    
    success_count = 0
    for i in range(0, len(audio_int16), chunk_samples):
        chunk = audio_int16[i:i + chunk_samples].tobytes()
        
        try:
            response = requests.post(
                f"{API_URL}/audio_to_blendshapes",
                data=chunk,
                headers={'Content-Type': 'audio/pcm'}
            )
            
            if response.status_code == 200:
                success_count += 1
            
        except:
            pass
        
        time.sleep(chunk_duration)
    
    print(f"Chunks traités avec succès: {success_count}")
    return success_count > 0

def main():
    """Programme principal"""
    print("=== Test API PCM Direct ===")
    print(f"API: {API_URL}")
    print()
    
    # Vérifier l'API
    if not test_health():
        print("API non accessible")
        return
    
    # Tests
    tests = [
        ("PCM Direct", test_direct_pcm),
        ("Buffer System", test_buffer_system),
        ("Audio Parole", test_realistic_speech)
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*40}")
        print(f"Test: {test_name}")
        print('='*40)
        
        try:
            if test_func():
                print(f"✓ {test_name} réussi")
            else:
                print(f"✗ {test_name} échoué")
        except Exception as e:
            print(f"✗ {test_name} exception: {e}")
        
        time.sleep(1)
    
    print("\n=== Tests terminés ===")
    
    # État final
    print("\nÉtat final:")
    test_health()

if __name__ == "__main__":
    main()