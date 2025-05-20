#!/usr/bin/env python3
"""
Outil pour analyser les captures de paquets LiveLink
Permet de comparer avec le format NeuroSync_Player qui fonctionne
"""

import sys
import struct
import binascii
from pathlib import Path

def analyze_packet(data):
    """Analyse un paquet LiveLink"""
    print(f"\n=== Analyse du paquet LiveLink ===")
    print(f"Taille totale: {len(data)} octets")
    
    if len(data) < 64:
        print("Paquet trop court pour être analysé")
        return
    
    offset = 0
    
    # Version (4 octets, little-endian)
    version = struct.unpack('<I', data[offset:offset+4])[0]
    print(f"Version: {version}")
    offset += 4
    
    # UUID (36 octets ASCII)
    uuid_bytes = data[offset:offset+36]
    uuid_str = uuid_bytes.decode('utf-8', errors='ignore')
    print(f"UUID: '{uuid_str}'")
    print(f"UUID hex: {uuid_bytes.hex()}")
    offset += 36
    
    # Name length (4 octets, big-endian)
    name_length = struct.unpack('!I', data[offset:offset+4])[0]
    print(f"Name length: {name_length}")
    offset += 4
    
    # Name (variable length)
    name_bytes = data[offset:offset+name_length]
    name_str = name_bytes.decode('utf-8', errors='ignore')
    print(f"Name: '{name_str}'")
    offset += name_length
    
    # Frames (8 octets - 2x unsigned int)
    frames, subframe = struct.unpack("!II", data[offset:offset+8])
    print(f"Frames: {frames}, Subframe: {subframe}")
    offset += 8
    
    # Frame rate (8 octets - 2x unsigned int)
    fps, denominator = struct.unpack("!II", data[offset:offset+8])
    print(f"FPS: {fps}, Denominator: {denominator}")
    offset += 8
    
    # Blendshapes count (1 octet)
    blendshapes_count = struct.unpack('!B', data[offset:offset+1])[0]
    print(f"Blendshapes count: {blendshapes_count}")
    offset += 1
    
    # Blendshapes values (float32 x count)
    print("\nBlendshapes:")
    for i in range(min(blendshapes_count, 10)):  # Afficher les 10 premiers
        if offset + 4 <= len(data):
            value = struct.unpack('!f', data[offset:offset+4])[0]
            print(f"  [{i}]: {value:.4f}")
            offset += 4
    
    if blendshapes_count > 10:
        print(f"  ... ({blendshapes_count - 10} autres valeurs)")
    
    # Hex dump des 256 premiers octets
    print("\nHex dump (256 premiers octets):")
    for i in range(0, min(256, len(data)), 16):
        hex_str = data[i:i+16].hex(' ')
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data[i:i+16])
        print(f"{i:04x}: {hex_str:<48} |{ascii_str}|")

def compare_packets(packet1, packet2):
    """Compare deux paquets LiveLink"""
    print("\n=== Comparaison de paquets ===")
    print(f"Taille paquet 1: {len(packet1)} octets")
    print(f"Taille paquet 2: {len(packet2)} octets")
    
    if len(packet1) != len(packet2):
        print("⚠️ Les paquets ont des tailles différentes")
    
    # Comparer octet par octet
    differences = []
    for i in range(min(len(packet1), len(packet2))):
        if packet1[i] != packet2[i]:
            differences.append((i, packet1[i], packet2[i]))
    
    print(f"\nNombre de différences: {len(differences)}")
    
    # Afficher les 20 premières différences
    for i, (offset, val1, val2) in enumerate(differences[:20]):
        print(f"Offset {offset:04x}: {val1:02x} -> {val2:02x}")
    
    if len(differences) > 20:
        print(f"... et {len(differences) - 20} autres différences")

def extract_blendshapes(data):
    """Extrait les valeurs de blendshapes d'un paquet"""
    try:
        # Même logique que analyze_packet mais retourne juste les blendshapes
        offset = 4  # Version
        offset += 36  # UUID
        name_length = struct.unpack('!I', data[offset:offset+4])[0]
        offset += 4 + name_length  # Name length + name
        offset += 16  # Frames + Frame rate
        
        blendshapes_count = struct.unpack('!B', data[offset:offset+1])[0]
        offset += 1
        
        blendshapes = []
        for i in range(blendshapes_count):
            if offset + 4 <= len(data):
                value = struct.unpack('!f', data[offset:offset+4])[0]
                blendshapes.append(value)
                offset += 4
        
        return blendshapes
    except Exception as e:
        print(f"Erreur extraction blendshapes: {e}")
        return []

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_livelink_capture.py <packet_file> [packet_file2]")
        print("  Pour analyser un paquet: python analyze_livelink_capture.py packet.bin")
        print("  Pour comparer deux paquets: python analyze_livelink_capture.py packet1.bin packet2.bin")
        sys.exit(1)
    
    # Charger le premier paquet
    packet_file1 = Path(sys.argv[1])
    if not packet_file1.exists():
        print(f"Fichier non trouvé: {packet_file1}")
        sys.exit(1)
    
    with open(packet_file1, 'rb') as f:
        packet1 = f.read()
    
    print(f"Analyse de: {packet_file1}")
    analyze_packet(packet1)
    
    # Si un deuxième fichier est fourni, comparer
    if len(sys.argv) > 2:
        packet_file2 = Path(sys.argv[2])
        if not packet_file2.exists():
            print(f"Fichier non trouvé: {packet_file2}")
            sys.exit(1)
        
        with open(packet_file2, 'rb') as f:
            packet2 = f.read()
        
        print(f"\n\nAnalyse de: {packet_file2}")
        analyze_packet(packet2)
        
        compare_packets(packet1, packet2)
        
        # Comparer les blendshapes
        blendshapes1 = extract_blendshapes(packet1)
        blendshapes2 = extract_blendshapes(packet2)
        
        print("\n=== Comparaison des blendshapes ===")
        print(f"Nombre de blendshapes paquet 1: {len(blendshapes1)}")
        print(f"Nombre de blendshapes paquet 2: {len(blendshapes2)}")
        
        if blendshapes1 and blendshapes2:
            print("\nValeurs non-nulles:")
            for i in range(min(len(blendshapes1), len(blendshapes2))):
                if blendshapes1[i] != 0 or blendshapes2[i] != 0:
                    print(f"  [{i}]: {blendshapes1[i]:.4f} -> {blendshapes2[i]:.4f}")

if __name__ == "__main__":
    main()