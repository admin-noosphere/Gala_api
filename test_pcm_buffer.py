#!/usr/bin/env python3
"""
Test complet du système PCM avec buffer
"""

import requests
import numpy as np
import time
import json

# Configuration
API_URL = "http://localhost:6969"
SAMPLE_RATE = 16000

def test_health_detailed():
    """Test détaillé de l'état de l'API"""
    print("=== Test Health Détaillé ===")
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            health = response.json()
            print(f"Status: {health['status']}")
            print(f"Modèle chargé: {health['model_loaded']}")
            print(f"LiveLink connecté: {health['livelink_connected']}")
            print(f"GPU: {health['gpu']}")
            print(f"Buffer: {health['buffer_level']}/{health['buffer_max']} bytes")
            print(f"Buffer rempli à: {health['buffer_level']/health['buffer_max']*100:.1f}%")
            return True
    except Exception as e:
        print(f"Erreur: {e}")
    return False

def generate_speech_audio(duration=2.0):
    """Génère un audio PCM simulant la parole"""
    samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, samples)
    
    # Voix avec variations
    base_freq = 150
    # Variation de fréquence pour simuler l'intonation
    freq_variation = 30 * np.sin(2 * np.pi * 1.5 * t)
    frequency = base_freq + freq_variation
    
    # Signal principal
    audio = 0.5 * np.sin(2 * np.pi * frequency * t)
    
    # Harmoniques
    audio += 0.3 * np.sin(2 * np.pi * frequency * 2 * t)
    audio += 0.1 * np.sin(2 * np.pi * frequency * 3 * t)
    
    # Enveloppe pour simuler les mots
    envelope = np.ones_like(t)
    # Créer des "mots" avec des pauses
    for i in range(0, len(t), SAMPLE_RATE // 2):  # Tous les 0.5s
        pause_start = i + SAMPLE_RATE // 3
        pause_end = i + SAMPLE_RATE // 3 + SAMPLE_RATE // 10
        if pause_end < len(envelope):
            envelope[pause_start:pause_end] *= 0.1
    
    audio *= envelope
    
    # Normaliser et convertir en PCM 16-bit
    audio = audio / np.max(np.abs(audio))
    audio_int16 = (audio * 16000).astype(np.int16)
    
    return audio_int16.tobytes()

def test_buffer_system():
    """Test du système de buffer avec envoi progressif"""
    print("\n=== Test Système de Buffer ===")
    
    # Générer 3 secondes d'audio
    audio_data = generate_speech_audio(3.0)
    total_size = len(audio_data)
    chunk_size = 1024  # Petits chunks pour tester le buffer
    
    print(f"Audio total: {total_size} bytes")
    print(f"Chunks: {chunk_size} bytes")
    print(f"Nombre de chunks: {total_size // chunk_size}")
    
    # Envoyer progressivement
    sent_bytes = 0
    chunk_count = 0
    
    for i in range(0, total_size, chunk_size):
        chunk = audio_data[i:i + chunk_size]
        
        try:
            response = requests.post(
                f"{API_URL}/audio_to_blendshapes",
                data=chunk,
                headers={'Content-Type': 'audio/pcm'}
            )
            
            if response.status_code == 200:
                data = response.json()
                sent_bytes += len(chunk)
                chunk_count += 1
                
                # Afficher le progrès tous les 10 chunks
                if chunk_count % 10 == 0:
                    buffer_pct = data['buffer_level'] / 6144 * 100
                    print(f"Chunk {chunk_count}: {sent_bytes} bytes envoyés, "
                          f"Buffer: {data['buffer_level']}/6144 ({buffer_pct:.1f}%)")
            else:
                print(f"Erreur chunk {chunk_count}: {response.status_code}")
                
        except Exception as e:
            print(f"Exception chunk {chunk_count}: {e}")
            break
        
        # Simuler le timing réel
        time.sleep(chunk_size / SAMPLE_RATE / 2)  # /2 car 16-bit
    
    print(f"\nTotal envoyé: {sent_bytes} bytes en {chunk_count} chunks")
    
    # Flush final
    try:
        response = requests.post(f"{API_URL}/flush_buffer")
        print("Buffer flush demandé")
    except:
        pass
    
    # Vérifier l'état final
    time.sleep(1)
    test_health_detailed()

def test_realtime_speech():
    """Test avec simulation de parole en temps réel"""
    print("\n=== Test Parole Temps Réel ===")
    
    # Simuler 5 secondes de conversation
    duration = 5.0
    chunk_duration = 0.032  # 32ms chunks
    samples_per_chunk = int(SAMPLE_RATE * chunk_duration)
    
    print(f"Simulation de {duration}s de parole")
    print(f"Chunks de {chunk_duration*1000:.0f}ms")
    
    start_time = time.time()
    chunks_sent = 0
    
    while time.time() - start_time < duration:
        # Générer un chunk en temps réel
        t_start = time.time() - start_time
        t = np.linspace(t_start, t_start + chunk_duration, samples_per_chunk)
        
        # Voix avec variation
        freq = 150 + 50 * np.sin(2 * np.pi * 2 * t_start)
        audio = 0.5 * np.sin(2 * np.pi * freq * t)
        
        # Modulation
        if int(t_start) % 2 == 0:  # Parole active
            audio *= 1.0
        else:  # Pause
            audio *= 0.1
        
        # Convertir en PCM
        audio_int16 = (audio * 16000).astype(np.int16)
        
        # Envoyer
        try:
            response = requests.post(
                f"{API_URL}/audio_to_blendshapes",
                data=audio_int16.tobytes(),
                headers={'Content-Type': 'audio/pcm'}
            )
            
            if response.status_code == 200:
                chunks_sent += 1
                if chunks_sent % 30 == 0:  # ~1 fois par seconde
                    print(f"Temps: {time.time() - start_time:.1f}s, "
                          f"Chunks: {chunks_sent}")
            
        except Exception as e:
            print(f"Erreur: {e}")
            break
        
        # Attendre avant le prochain chunk
        time.sleep(chunk_duration)
    
    print(f"\nFin: {chunks_sent} chunks envoyés en {time.time() - start_time:.1f}s")

def main():
    """Programme principal"""
    print("=== Test PCM Buffer System ===")
    print(f"API: {API_URL}")
    print()
    
    # Vérifier l'API
    if not test_health_detailed():
        print("API non accessible")
        return
    
    # Tests
    tests = [
        ("Système de Buffer", test_buffer_system),
        ("Parole Temps Réel", test_realtime_speech)
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Test: {test_name}")
        print('='*50)
        
        try:
            test_func()
            print(f"\n✓ {test_name} terminé")
        except Exception as e:
            print(f"\n✗ {test_name} échoué: {e}")
        
        time.sleep(2)
    
    print("\n=== Tests terminés ===")
    
    # État final
    print("\nÉtat final de l'API:")
    test_health_detailed()

if __name__ == "__main__":
    main()