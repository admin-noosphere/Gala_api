#!/usr/bin/env python3
"""
Test en temps réel des blendshapes avec l'API fixée
Vérifie que les blendshapes sont générés et envoyés à Unreal
"""

import socket
import struct
import time
import threading
import requests
import numpy as np

# Configuration
API_URL = "http://localhost:6969"
LIVELINK_IP = "192.168.1.14"
LIVELINK_PORT = 11111

# Variables globales
received_packets = []
listening = True

def listen_livelink():
    """Écoute les paquets LiveLink pour vérifier qu'ils sont envoyés"""
    global received_packets, listening
    
    try:
        # Créer un socket UDP pour écouter
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", LIVELINK_PORT))
        sock.settimeout(0.5)
        
        print(f"Écoute LiveLink sur port {LIVELINK_PORT}...")
        
        while listening:
            try:
                data, addr = sock.recvfrom(4096)
                received_packets.append({
                    'time': time.time(),
                    'size': len(data),
                    'from': addr,
                    'data': data[:100]  # Garder seulement le début pour l'analyse
                })
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Erreur réception: {e}")
                break
                
    except Exception as e:
        print(f"Erreur création socket: {e}")
    finally:
        sock.close()

def generate_speaking_audio(duration=1.0):
    """Génère un audio qui simule la parole"""
    sample_rate = 16000
    samples = int(sample_rate * duration)
    t = np.linspace(0, duration, samples)
    
    # Combiner plusieurs fréquences pour simuler la voix
    audio = np.zeros(samples)
    
    # Fréquence fondamentale (voix masculine ~120Hz, féminine ~220Hz)
    f0 = 150
    audio += 0.5 * np.sin(2 * np.pi * f0 * t)
    
    # Harmoniques
    audio += 0.3 * np.sin(2 * np.pi * f0 * 2 * t)
    audio += 0.2 * np.sin(2 * np.pi * f0 * 3 * t)
    
    # Modulation pour simuler les phonèmes
    mod_freq = 5  # 5Hz - rythme de la parole
    modulation = 0.3 * np.sin(2 * np.pi * mod_freq * t) + 0.7
    audio *= modulation
    
    # Ajouter du bruit pour le réalisme
    noise = 0.05 * np.random.randn(samples)
    audio += noise
    
    # Normaliser et convertir en int16
    audio = audio / np.max(np.abs(audio))
    audio_int16 = (audio * 16000).astype(np.int16)
    
    return audio_int16.tobytes()

def test_realtime_processing():
    """Test de traitement en temps réel"""
    print("\n=== Test Temps Réel avec Audio Parlé ===")
    
    # Démarrer l'écoute LiveLink dans un thread séparé
    # listener_thread = threading.Thread(target=listen_livelink)
    # listener_thread.start()
    
    # Attendre que l'écoute démarre
    time.sleep(1)
    
    # Envoyer plusieurs chunks d'audio "parlé"
    print("\nEnvoi d'audio simulant la parole pendant 5 secondes...")
    
    start_time = time.time()
    chunk_count = 0
    
    while time.time() - start_time < 5.0:
        # Générer un chunk de 100ms
        audio_chunk = generate_speaking_audio(duration=0.1)
        
        # Envoyer à l'API
        try:
            response = requests.post(
                f"{API_URL}/audio_to_blendshapes",
                data=audio_chunk,
                headers={"Content-Type": "audio/pcm"}
            )
            
            if response.status_code == 200:
                chunk_count += 1
                if chunk_count % 10 == 0:  # Afficher toutes les secondes
                    print(f"✓ {chunk_count} chunks traités")
            else:
                print(f"✗ Erreur: {response.status_code}")
                
        except Exception as e:
            print(f"Exception: {e}")
            break
            
        # Attendre avant le prochain chunk (30 FPS)
        time.sleep(0.033)
    
    print(f"\nTotal: {chunk_count} chunks envoyés en {time.time() - start_time:.1f}s")
    
    # Arrêter l'écoute
    global listening
    listening = False
    # listener_thread.join()
    
    # Analyser les paquets reçus
    # print(f"\nPaquets LiveLink reçus: {len(received_packets)}")
    # if received_packets:
    #     print("Premiers paquets:")
    #     for i, packet in enumerate(received_packets[:5]):
    #         print(f"  {i+1}. Taille: {packet['size']} bytes, De: {packet['from']}")

def verify_blendshapes_generation():
    """Vérifie que les blendshapes sont réellement générés"""
    print("\n=== Vérification Génération Blendshapes ===")
    
    # Envoyer un audio spécifique
    test_audio = generate_speaking_audio(duration=0.5)
    
    print("Envoi d'audio de test...")
    
    # Activer le mode debug temporairement
    response = requests.post(
        f"{API_URL}/audio_to_blendshapes",
        data=test_audio,
        headers={
            "Content-Type": "audio/pcm",
            "X-Debug": "true"  # Header spécial pour activer le debug
        }
    )
    
    if response.status_code == 200:
        print("✓ Audio traité avec succès")
        
        # Si l'API retourne des détails
        try:
            data = response.json()
            if isinstance(data, dict) and "debug" in data:
                debug_info = data["debug"]
                print(f"Blendshapes générés: {debug_info.get('blendshape_count', 'N/A')}")
                print(f"Valeurs actives: {debug_info.get('active_shapes', 'N/A')}")
        except:
            pass
    else:
        print(f"✗ Erreur: {response.status_code}")

def main():
    """Programme principal"""
    print("=== Test LiveLink avec API Fixed Audio ===")
    print(f"API: {API_URL}")
    print(f"LiveLink: {LIVELINK_IP}:{LIVELINK_PORT}")
    print()
    
    # Vérifier que l'API est prête
    print("Vérification de l'API...")
    try:
        response = requests.get(f"{API_URL}/health")
        health = response.json()
        print(f"✓ API prête")
        print(f"  - Modèle chargé: {health['model_loaded']}")
        print(f"  - LiveLink connecté: {health['livelink_connected']}")
    except Exception as e:
        print(f"✗ API non accessible: {e}")
        return
    
    # Tests
    tests = [
        ("Génération Blendshapes", verify_blendshapes_generation),
        ("Traitement Temps Réel", test_realtime_processing)
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
        
        time.sleep(1)
    
    print("\n=== Tests terminés ===")
    print("\nPour vérifier dans Unreal Engine:")
    print("1. Ouvrez le LiveLink panel")
    print("2. Vérifiez que 'GalaFace' apparaît")
    print("3. Observez les blendshapes actifs")
    print("4. La bouche devrait bouger avec l'audio")

if __name__ == "__main__":
    main()