#!/usr/bin/env python3
"""
Compare les implémentations NeuroSync_Player et Gala
"""

import socket
import time
import uuid as uuid_lib
from modules.pylivelinkface import PyLiveLinkFace, FaceBlendShape


def test_neurosync_style():
    """Test avec l'approche exacte de NeuroSync_Player"""
    print("=== Test style NeuroSync_Player ===")
    
    UDP_IP = "192.168.1.14"
    UDP_PORT = 11111
    
    # Socket direct
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((UDP_IP, UDP_PORT))
    
    # PyLiveLinkFace avec UUID spécifique
    py_face = PyLiveLinkFace()
    print(f"UUID par défaut: {py_face.uuid}")
    
    # Initialiser à zéro
    for i in range(52):
        py_face.set_blendshape(FaceBlendShape(i), 0.0)
    
    # Test 1: Position neutre
    print("\n1. Envoi position neutre...")
    data = py_face.encode()
    print(f"Taille: {len(data)} octets")
    s.sendall(data)
    time.sleep(1)
    
    # Test 2: Ouvrir/fermer la bouche
    print("\n2. Animation bouche...")
    for i in range(30):
        # Reset
        for j in range(52):
            py_face.set_blendshape(FaceBlendShape(j), 0.0)
        
        # JawOpen progressif
        value = i / 30.0
        py_face.set_blendshape(FaceBlendShape.JawOpen, value)
        
        # Envoyer
        s.sendall(py_face.encode())
        
        if i % 10 == 0:
            print(f"  Frame {i}: JawOpen = {value:.2f}")
        
        time.sleep(0.033)
    
    # Test 3: Clignement
    print("\n3. Test clignement...")
    for i in range(20):
        # Reset
        for j in range(52):
            py_face.set_blendshape(FaceBlendShape(j), 0.0)
        
        # Clignement
        if i < 10:
            value = i / 10.0
        else:
            value = (20 - i) / 10.0
        
        py_face.set_blendshape(FaceBlendShape.EyeBlinkLeft, value)
        py_face.set_blendshape(FaceBlendShape.EyeBlinkRight, value)
        
        s.sendall(py_face.encode())
        time.sleep(0.05)
    
    # Reset final
    for j in range(52):
        py_face.set_blendshape(FaceBlendShape(j), 0.0)
    s.sendall(py_face.encode())
    
    s.close()
    print("\nTest terminé")


def test_different_uuids():
    """Test avec différents formats d'UUID"""
    print("\n=== Test différents UUIDs ===")
    
    UDP_IP = "192.168.1.14"
    UDP_PORT = 11111
    
    # Liste d'UUIDs à tester
    uuids_to_test = [
        str(uuid_lib.uuid1()),                     # UUID v1 normal
        str(uuid_lib.uuid4()),                     # UUID v4 random
        "${" + str(uuid_lib.uuid1()) + "}",       # Format NeuroSync avec ${}
        "$" + str(uuid_lib.uuid1()),              # Format NeuroSync avec $
        "GalaFace",                               # String simple
    ]
    
    for test_uuid in uuids_to_test:
        print(f"\nTest avec UUID: {test_uuid}")
        
        # Créer socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((UDP_IP, UDP_PORT))
        
        # Créer PyLiveLinkFace avec cet UUID
        py_face = PyLiveLinkFace(uuid_str=test_uuid)
        
        # Test simple: ouvrir la bouche
        py_face.reset()
        py_face.set_blendshape(FaceBlendShape.JawOpen, 0.8)
        
        # Envoyer plusieurs fois
        for _ in range(30):
            s.sendall(py_face.encode())
            time.sleep(0.033)
        
        # Reset
        py_face.reset()
        s.sendall(py_face.encode())
        
        s.close()
        time.sleep(1)


def main():
    test_neurosync_style()
    test_different_uuids()


if __name__ == "__main__":
    main()