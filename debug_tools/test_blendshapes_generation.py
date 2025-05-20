#!/usr/bin/env python3
"""
Test de génération de blendshapes avec différents formats audio
Compare les résultats avec l'API Real-Time originale
"""

import sys
import wave
import numpy as np
import requests
import json
from pathlib import Path

# Audio de test
def generate_test_audio(duration=1.0, sample_rate=16000, frequency=440):
    """Génère un audio de test sinusoïdal"""
    samples = int(sample_rate * duration)
    t = np.linspace(0, duration, samples)
    audio = np.sin(2 * np.pi * frequency * t)
    
    # Convertir en int16
    audio_int16 = (audio * 32767).astype(np.int16)
    return audio_int16

def create_wav_file(audio_data, sample_rate=16000, filename="test.wav"):
    """Crée un fichier WAV à partir de données audio"""
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data.tobytes())
    return filename

def test_audio_formats():
    """Test différents formats audio"""
    results = {}
    
    # Format 1: Audio brut PCM
    print("Test 1: Audio brut PCM...")
    audio_pcm = generate_test_audio()
    results['pcm_raw'] = test_api(audio_pcm.tobytes(), content_type="audio/raw")
    
    # Format 2: Fichier WAV
    print("\nTest 2: Fichier WAV...")
    wav_file = create_wav_file(audio_pcm)
    with open(wav_file, 'rb') as f:
        wav_data = f.read()
    results['wav_file'] = test_api(wav_data, content_type="audio/wav")
    
    # Format 3: WAV en mémoire
    print("\nTest 3: WAV en mémoire...")
    import io
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(audio_pcm.tobytes())
    wav_buffer.seek(0)
    results['wav_memory'] = test_api(wav_buffer.read(), content_type="audio/wav")
    
    # Format 4: Différentes fréquences d'échantillonnage
    print("\nTest 4: Différentes fréquences...")
    for rate in [16000, 44100, 48000]:
        audio_test = generate_test_audio(sample_rate=rate)
        wav_test = io.BytesIO()
        with wave.open(wav_test, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(rate)
            wf.writeframes(audio_test.tobytes())
        wav_test.seek(0)
        results[f'rate_{rate}'] = test_api(wav_test.read(), content_type="audio/wav")
    
    return results

def test_api(audio_data, content_type="audio/wav", api_url="http://localhost:6969/audio_to_blendshapes"):
    """Test l'API avec des données audio"""
    try:
        response = requests.post(
            api_url,
            data=audio_data,
            headers={'Content-Type': content_type}
        )
        
        result = {
            'status_code': response.status_code,
            'success': response.status_code == 200
        }
        
        if response.status_code == 200:
            data = response.json()
            blendshapes = data.get('blendshapes', [])
            
            result['blendshapes_info'] = {
                'type': type(blendshapes).__name__,
                'count': len(blendshapes) if isinstance(blendshapes, list) else 0
            }
            
            if isinstance(blendshapes, list) and len(blendshapes) > 0:
                first = blendshapes[0]
                if isinstance(first, list):
                    result['blendshapes_info']['format'] = 'list_of_frames'
                    result['blendshapes_info']['num_frames'] = len(blendshapes)
                    result['blendshapes_info']['values_per_frame'] = len(first)
                else:
                    result['blendshapes_info']['format'] = 'single_frame'
                    result['blendshapes_info']['num_values'] = len(blendshapes)
                
                # Analyser les valeurs
                non_zero = sum(1 for v in (first if isinstance(first, list) else blendshapes) if v != 0)
                result['blendshapes_info']['non_zero_count'] = non_zero
        else:
            result['error'] = response.text
            
    except Exception as e:
        result = {
            'success': False,
            'error': str(e)
        }
    
    return result

def compare_apis():
    """Compare notre API avec l'API Real-Time"""
    print("=== Comparaison des APIs ===")
    
    # Créer un audio de test
    audio_data = generate_test_audio(duration=2.0)
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(audio_data.tobytes())
    wav_buffer.seek(0)
    test_audio = wav_buffer.read()
    
    # Tester notre API
    print("\n1. Test de notre API...")
    our_result = test_api(test_audio, api_url="http://localhost:6969/audio_to_blendshapes")
    
    # Tester l'API Real-Time (si disponible sur un autre port)
    print("\n2. Test de l'API Real-Time...")
    realtime_result = test_api(test_audio, api_url="http://localhost:6970/audio_to_blendshapes")
    
    # Comparer
    print("\n=== Résultats ===")
    print("Notre API:", json.dumps(our_result, indent=2))
    print("\nAPI Real-Time:", json.dumps(realtime_result, indent=2))
    
    return our_result, realtime_result

def analyze_blendshapes_values(blendshapes):
    """Analyse les valeurs de blendshapes"""
    print("\n=== Analyse des valeurs ===")
    
    if isinstance(blendshapes, list):
        if len(blendshapes) > 0 and isinstance(blendshapes[0], list):
            # Analyse de toutes les frames
            print(f"Nombre de frames: {len(blendshapes)}")
            
            for i, frame in enumerate(blendshapes[:5]):  # Analyser les 5 premières
                print(f"\nFrame {i}:")
                analyze_single_frame(frame)
        else:
            # Frame unique
            print("Frame unique:")
            analyze_single_frame(blendshapes)

def analyze_single_frame(values):
    """Analyse une frame de blendshapes"""
    if not values:
        print("  Aucune valeur")
        return
    
    print(f"  Nombre de valeurs: {len(values)}")
    print(f"  Min: {min(values):.4f}, Max: {max(values):.4f}")
    print(f"  Moyenne: {np.mean(values):.4f}")
    
    # Valeurs non-nulles
    non_zero = [(i, v) for i, v in enumerate(values) if abs(v) > 0.001]
    print(f"  Valeurs non-nulles: {len(non_zero)}")
    
    for i, (idx, val) in enumerate(non_zero[:10]):
        print(f"    [{idx}]: {val:.4f}")
    
    if len(non_zero) > 10:
        print(f"    ... et {len(non_zero) - 10} autres")

if __name__ == "__main__":
    import io
    
    print("🧪 Test de génération de blendshapes")
    print("="*40)
    
    # Test 1: Formats audio
    print("\n1. Test des différents formats audio")
    format_results = test_audio_formats()
    
    print("\n📊 Résumé des formats:")
    for format_name, result in format_results.items():
        print(f"  {format_name}: {'✅' if result['success'] else '❌'}")
        if result['success'] and 'blendshapes_info' in result:
            info = result['blendshapes_info']
            print(f"    Format: {info.get('format', 'unknown')}")
            print(f"    Non-zero: {info.get('non_zero_count', 0)}")
    
    # Test 2: Comparaison avec l'API Real-Time
    if "--compare" in sys.argv:
        print("\n2. Comparaison avec l'API Real-Time")
        compare_apis()
    
    # Test 3: Analyse détaillée
    print("\n3. Analyse détaillée d'un test")
    test_audio = generate_test_audio(duration=3.0)
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(test_audio.tobytes())
    wav_buffer.seek(0)
    
    response = requests.post(
        "http://localhost:6969/audio_to_blendshapes",
        data=wav_buffer.read(),
        headers={'Content-Type': 'audio/wav'}
    )
    
    if response.status_code == 200:
        data = response.json()
        blendshapes = data.get('blendshapes', [])
        analyze_blendshapes_values(blendshapes)
    
    print("\n✅ Tests terminés")
    print(f"Consultez les logs dans: debug_logs/")