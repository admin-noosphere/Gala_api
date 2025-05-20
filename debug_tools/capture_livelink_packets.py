#!/usr/bin/env python3
"""
Capture les paquets LiveLink pour analyse
Peut capturer depuis NeuroSync_Player ou notre API
"""

import socket
import time
import sys
from datetime import datetime
from pathlib import Path

def capture_packets(ip="0.0.0.0", port=11111, duration=10, output_dir="captures"):
    """
    Capture les paquets UDP LiveLink
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Créer un socket UDP pour écouter
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((ip, port))
    sock.settimeout(1.0)  # Timeout pour permettre l'interruption
    
    print(f"📡 Écoute sur {ip}:{port} pendant {duration} secondes...")
    print("Assurez-vous qu'Unreal Engine n'écoute pas sur ce port")
    print("Lancez l'application qui envoie les paquets LiveLink")
    print()
    
    start_time = time.time()
    packet_count = 0
    
    try:
        while time.time() - start_time < duration:
            try:
                data, addr = sock.recvfrom(65535)  # Buffer max UDP
                packet_count += 1
                
                # Sauvegarder le paquet
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                filename = output_path / f"packet_{packet_count:04d}_{timestamp}.bin"
                
                with open(filename, 'wb') as f:
                    f.write(data)
                
                print(f"✅ Paquet {packet_count} capturé: {len(data)} octets de {addr}")
                print(f"   Sauvé dans: {filename}")
                
                # Aperçu rapide
                if len(data) >= 64:
                    print(f"   Début: {data[:32].hex()}")
                    print()
                
            except socket.timeout:
                continue
            except KeyboardInterrupt:
                break
                
    except Exception as e:
        print(f"Erreur: {e}")
    finally:
        sock.close()
    
    print(f"\n📊 Capture terminée: {packet_count} paquets capturés")
    print(f"📁 Fichiers sauvés dans: {output_path}")

def compare_sources():
    """
    Capture et compare les paquets de différentes sources
    """
    print("=== Comparaison NeuroSync_Player vs Notre API ===")
    print()
    
    # Étape 1: Capturer depuis NeuroSync_Player
    print("1. Lancez d'abord NeuroSync_Player (wave_to_face.py)")
    print("   Appuyez sur Entrée quand prêt...")
    input()
    
    print("Capture des paquets NeuroSync_Player...")
    capture_packets(duration=5, output_dir="captures/neurosync_player")
    
    print("\n2. Arrêtez NeuroSync_Player et lancez notre API")
    print("   Appuyez sur Entrée quand prêt...")
    input()
    
    print("Capture des paquets de notre API...")
    capture_packets(duration=5, output_dir="captures/our_api")
    
    print("\n✅ Captures terminées!")
    print("Utilisez analyze_livelink_capture.py pour comparer les paquets")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "compare":
        compare_sources()
    else:
        # Capture simple
        duration = int(sys.argv[1]) if len(sys.argv> 1 else 10
        capture_packets(duration=duration)