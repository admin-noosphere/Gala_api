#!/usr/bin/env python3
"""
Script de débogage pour comparer les envois LiveLink
"""

import socket
import time
import struct
from modules.pylivelinkface import PyLiveLinkFace, FaceBlendShape


def test_simple_debug():
    """Test simple avec debug des données"""
    print("=== Test de débogage LiveLink ===")
    
    UDP_IP = "192.168.1.14"
    UDP_PORT = 11111
    
    # Créer socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((UDP_IP, UDP_PORT))
    
    # Créer PyLiveLinkFace
    py_face = PyLiveLinkFace()
    
    # Test 1: Tout à zéro
    print("\n1. Envoi position neutre (tout à 0)...")
    for i in range(52):
        py_face.set_blendshape(FaceBlendShape(i), 0.0)
    
    data = py_face.encode()
    print(f"Taille des données: {len(data)} octets")
    print(f"Premiers 32 octets: {data[:32].hex()}")
    
    s.sendall(data)
    time.sleep(1)
    
    # Test 2: Bouche ouverte
    print("\n2. Envoi bouche ouverte (JawOpen = 1.0)...")
    py_face.reset()
    py_face.set_blendshape(FaceBlendShape.JawOpen, 1.0)
    
    data = py_face.encode()
    s.sendall(data)
    time.sleep(1)
    
    # Test 3: Yeux fermés
    print("\n3. Envoi yeux fermés...")
    py_face.reset()
    py_face.set_blendshape(FaceBlendShape.EyeBlinkLeft, 1.0)
    py_face.set_blendshape(FaceBlendShape.EyeBlinkRight, 1.0)
    
    data = py_face.encode()
    s.sendall(data)
    time.sleep(1)
    
    # Test 4: Sourire
    print("\n4. Envoi sourire...")
    py_face.reset()
    py_face.set_blendshape(FaceBlendShape.MouthSmileLeft, 0.5)
    py_face.set_blendshape(FaceBlendShape.MouthSmileRight, 0.5)
    
    data = py_face.encode()
    s.sendall(data)
    time.sleep(1)
    
    # Test 5: Animation simple
    print("\n5. Animation simple (bouche qui s'ouvre et se ferme)...")
    for i in range(60):  # 2 secondes à 30 FPS
        py_face.reset()
        value = abs(i - 30) / 30.0  # 0 -> 1 -> 0
        py_face.set_blendshape(FaceBlendShape.JawOpen, value)
        
        data = py_face.encode()
        s.sendall(data)
        
        if i % 10 == 0:
            print(f"  Frame {i}: JawOpen = {value:.2f}")
        
        time.sleep(0.033)  # 30 FPS
    
    # Retour position neutre
    py_face.reset()
    s.sendall(py_face.encode())
    
    s.close()
    print("\nTest terminé")


def test_packet_comparison():
    """Compare les paquets avec différentes valeurs"""
    print("\n=== Comparaison des paquets ===")
    
    py_face = PyLiveLinkFace(name="TestFace")
    
    # Paquet 1: Tout à zéro
    py_face.reset()
    data1 = py_face.encode()
    
    # Paquet 2: JawOpen = 1.0
    py_face.reset()
    py_face.set_blendshape(FaceBlendShape.JawOpen, 1.0)
    data2 = py_face.encode()
    
    print(f"Taille paquet 1: {len(data1)} octets")
    print(f"Taille paquet 2: {len(data2)} octets")
    
    # Comparer les différences
    for i in range(min(len(data1), len(data2))):
        if data1[i] != data2[i]:
            print(f"Différence à l'octet {i}: {data1[i]:02x} -> {data2[i]:02x}")
    
    # Afficher les valeurs des blendshapes dans le paquet
    print("\nAnalyse du paquet 2 (JawOpen = 1.0):")
    # Le paquet commence par version (4), uuid (36), name_length (4), name (variable)
    # Puis frames (8), frame_rate (8), puis les données des blendshapes
    
    # Trouver où commencent les blendshapes
    offset = 4 + 36 + 4 + len("TestFace") + 8 + 8
    print(f"Offset des blendshapes: {offset}")
    
    # Lire le nombre de blendshapes (1 octet)
    num_shapes = struct.unpack('!B', data2[offset:offset+1])[0]
    print(f"Nombre de blendshapes: {num_shapes}")
    
    # Lire les valeurs (61 floats)
    offset += 1
    for i in range(min(20, num_shapes)):  # Afficher les 20 premiers
        value = struct.unpack('!f', data2[offset + i*4:offset + (i+1)*4])[0]
        if value != 0.0:
            print(f"  Blendshape {i}: {value}")


if __name__ == "__main__":
    test_simple_debug()
    test_packet_comparison()