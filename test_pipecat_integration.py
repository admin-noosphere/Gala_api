#!/usr/bin/env python3
"""
Test d'intégration avec Pipecat
Simule l'envoi d'audio depuis Pipecat vers l'API Gala
"""

import requests
import numpy as np
import time
import wave
import struct
from io import BytesIO

# Configuration
API_HOST = "192.168.1.32"
API_PORT = 6969
API_URL = f"http://{API_HOST}:{API_PORT}"

def create_test_audio(duration_sec: float = 1.0, frequency: float = 440.0) -> bytes:
    """
    Crée un audio de test (son sinusoïdal)
    
    Args:
        duration_sec: Durée en secondes
        frequency: Fréquence du son (440 Hz = La)
    
    Returns:
        Audio WAV en bytes
    """
    sample_rate = 48000
    channels = 1
    bit_depth = 16
    
    # Générer les échantillons
    num_samples = int(sample_rate * duration_sec)
    samples = []
    
    for i in range(num_samples):
        # Son sinusoïdal
        t = i / sample_rate
        value = 0.5 * np.sin(2 * np.pi * frequency * t)
        # Convertir en int16
        int_value = int(value * 32767)
        samples.append(int_value)
    
    # Créer un fichier WAV en mémoire
    wav_buffer = BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(bit_depth // 8)
        wav_file.setframerate(sample_rate)
        
        # Écrire les échantillons
        for sample in samples:
            wav_file.writeframes(struct.pack('<h', sample))
    
    return wav_buffer.getvalue()

def create_silence_audio(duration_sec: float = 1.0) -> bytes:
    """Crée un audio silencieux"""
    sample_rate = 48000
    channels = 1
    bit_depth = 16
    
    num_samples = int(sample_rate * duration_sec)
    
    # Créer un fichier WAV silencieux
    wav_buffer = BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(bit_depth // 8)
        wav_file.setframerate(sample_rate)
        
        # Écrire des zéros
        for _ in range(num_samples):
            wav_file.writeframes(struct.pack('<h', 0))
    
    return wav_buffer.getvalue()

def test_api_health():
    """Test l'endpoint de santé de l'API"""
    print("1. Test de l'endpoint /health...")
    
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ API en ligne")
            print(f"   Status: {data.get('status')}")
            print(f"   Version: {data.get('version')}")
            print(f"   Model: {data.get('model')}")
            return True
        else:
            print(f"   ✗ Erreur HTTP {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"   ✗ Impossible de se connecter à {API_URL}")
        return False
    except Exception as e:
        print(f"   ✗ Erreur: {e}")
        return False

def test_audio_to_blendshapes():
    """Test l'endpoint principal audio_to_blendshapes"""
    print("\n2. Test de l'endpoint /audio_to_blendshapes...")
    
    # Créer un audio de test
    test_audio = create_test_audio(duration_sec=0.5, frequency=440.0)
    
    try:
        response = requests.post(
            f"{API_URL}/audio_to_blendshapes",
            data=test_audio,
            headers={"Content-Type": "audio/wav"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            blendshapes = data.get("blendshapes", [])
            
            print(f"   ✓ Conversion réussie")
            print(f"   Nombre de blendshapes: {len(blendshapes)}")
            print(f"   Timestamp: {data.get('timestamp')}")
            print(f"   FPS cible: {data.get('fps')}")
            
            # Afficher quelques valeurs
            if blendshapes:
                print(f"   Valeurs min/max: {min(blendshapes):.3f} / {max(blendshapes):.3f}")
                print(f"   JawOpen: {blendshapes[17]:.3f}")
                print(f"   MouthSmile_L: {blendshapes[23]:.3f}")
            
            return True
        else:
            print(f"   ✗ Erreur HTTP {response.status_code}")
            print(f"   Réponse: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ✗ Erreur: {e}")
        return False

def test_streaming_simulation():
    """Simule un flux audio continu comme Pipecat"""
    print("\n3. Simulation de streaming audio...")
    
    # Paramètres du streaming
    chunk_duration = 0.1  # 100ms par chunk
    total_duration = 3    # 3 secondes au total
    
    print(f"   Envoi de chunks de {chunk_duration}s pendant {total_duration}s")
    
    success_count = 0
    error_count = 0
    
    start_time = time.time()
    while time.time() - start_time < total_duration:
        # Créer un chunk audio
        chunk_audio = create_test_audio(
            duration_sec=chunk_duration,
            frequency=440.0 + 100 * np.sin(time.time())  # Fréquence variable
        )
        
        try:
            response = requests.post(
                f"{API_URL}/audio_to_blendshapes",
                data=chunk_audio,
                headers={"Content-Type": "audio/wav"},
                timeout=5
            )
            
            if response.status_code == 200:
                success_count += 1
                if success_count % 10 == 0:
                    print(f"   ✓ {success_count} chunks envoyés avec succès")
            else:
                error_count += 1
                print(f"   ✗ Erreur chunk: {response.status_code}")
                
        except Exception as e:
            error_count += 1
            print(f"   ✗ Erreur: {e}")
        
        # Attendre avant le prochain chunk
        time.sleep(0.05)  # Laisser un peu de temps au serveur
    
    print(f"\n   Résumé:")
    print(f"   - Chunks réussis: {success_count}")
    print(f"   - Erreurs: {error_count}")
    print(f"   - Taux de succès: {success_count/(success_count+error_count)*100:.1f}%")
    
    return error_count == 0

def test_silence_handling():
    """Test comment l'API gère le silence"""
    print("\n4. Test avec audio silencieux...")
    
    silence_audio = create_silence_audio(duration_sec=0.5)
    
    try:
        response = requests.post(
            f"{API_URL}/audio_to_blendshapes",
            data=silence_audio,
            headers={"Content-Type": "audio/wav"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            blendshapes = data.get("blendshapes", [])
            
            print(f"   ✓ Traitement du silence réussi")
            print(f"   Blendshapes reçues: {len(blendshapes)}")
            
            # Vérifier si les valeurs sont proches de zéro (idle)
            max_value = max(abs(v) for v in blendshapes)
            print(f"   Valeur max absolue: {max_value:.3f}")
            
            if max_value < 0.1:
                print(f"   ✓ Valeurs proches de l'idle (< 0.1)")
            else:
                print(f"   ⚠ Valeurs élevées pour du silence")
            
            return True
        else:
            print(f"   ✗ Erreur HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ✗ Erreur: {e}")
        return False

def main():
    """Programme principal de test"""
    print("=== Test d'intégration Pipecat → Gala ===")
    print(f"API cible: {API_URL}")
    print()
    
    tests = [
        ("Santé API", test_api_health),
        ("Conversion audio → blendshapes", test_audio_to_blendshapes),
        ("Simulation streaming", test_streaming_simulation),
        ("Gestion du silence", test_silence_handling)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        success = test_func()
        results[test_name] = success
        time.sleep(0.5)  # Pause entre les tests
    
    # Résumé final
    print("\n=== Résumé des tests ===")
    for test_name, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{test_name}: {status}")
    
    # Recommandations
    print("\n=== Recommandations ===")
    
    if not results["Santé API"]:
        print("- Vérifier que l'API Gala est lancée sur 192.168.1.32:6969")
        print("- Vérifier le pare-feu et les connexions réseau")
    
    if results["Santé API"] and not results["Conversion audio → blendshapes"]:
        print("- Vérifier que le modèle NeuroSync est chargé")
        print("- Vérifier les logs de l'API pour les erreurs")
    
    if results["Gestion du silence"]:
        print("- L'API gère correctement le silence (idle)")
    
    print("\nPour l'intégration avec Pipecat:")
    print("1. Configurer Pipecat pour envoyer l'audio à http://192.168.1.32:6969/audio_to_blendshapes")
    print("2. Format audio: WAV, 48kHz, 16-bit, mono")
    print("3. Les blendshapes seront automatiquement envoyées à Unreal (192.168.1.14:11111)")

if __name__ == "__main__":
    main()