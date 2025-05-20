#!/usr/bin/env python3
"""
Test final LiveLink avec toutes les corrections
"""

import socket
import time
import numpy as np
from modules.pylivelinkface import PyLiveLinkFace, FaceBlendShape


def test_final():
    """Test final avec l'approche corrigée"""
    print("=== Test final LiveLink ===")
    
    UDP_IP = "192.168.1.14"
    UDP_PORT = 11111
    
    # 1. Socket direct comme NeuroSync_Player
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((UDP_IP, UDP_PORT))
    print(f"Socket connecté à {UDP_IP}:{UDP_PORT}")
    
    # 2. PyLiveLinkFace avec UUID correct
    py_face = PyLiveLinkFace(name="GalaFace", fps=60)
    print(f"UUID: {py_face.uuid}")
    
    # 3. Initialiser tous les blendshapes à 0
    for i in range(52):
        py_face.set_blendshape(FaceBlendShape(i), 0.0)
    
    # Test 1: Position neutre
    print("\n1. Position neutre...")
    data = py_face.encode()
    print(f"Taille paquet: {len(data)} octets")
    s.sendall(data)
    time.sleep(1)
    
    # Test 2: Animation bouche (progressive)
    print("\n2. Animation bouche...")
    for i in range(60):  # 2 secondes à 30 FPS
        # Reset
        for j in range(52):
            py_face.set_blendshape(FaceBlendShape(j), 0.0)
        
        # Ouvrir/fermer la bouche
        phase = (i / 60.0) * np.pi * 2
        value = abs(np.sin(phase))
        py_face.set_blendshape(FaceBlendShape.JawOpen, value)
        
        data = py_face.encode()
        s.sendall(data)
        
        if i % 10 == 0:
            print(f"  Frame {i}: JawOpen = {value:.2f}")
        
        time.sleep(0.033)  # ~30 FPS
    
    # Test 3: Clignement
    print("\n3. Test clignement...")
    for i in range(30):
        # Reset
        for j in range(52):
            py_face.set_blendshape(FaceBlendShape(j), 0.0)
        
        # Clignement rapide
        if i < 5:
            value = i / 5.0
        elif i < 10:
            value = (10 - i) / 5.0
        else:
            value = 0.0
        
        py_face.set_blendshape(FaceBlendShape.EyeBlinkLeft, value)
        py_face.set_blendshape(FaceBlendShape.EyeBlinkRight, value)
        
        s.sendall(py_face.encode())
        time.sleep(0.033)
    
    # Test 4: Sourire
    print("\n4. Test sourire...")
    for i in range(60):
        # Reset
        for j in range(52):
            py_face.set_blendshape(FaceBlendShape(j), 0.0)
        
        # Sourire progressif
        if i < 30:
            value = i / 30.0
        else:
            value = (60 - i) / 30.0
        
        py_face.set_blendshape(FaceBlendShape.MouthSmileLeft, value * 0.7)
        py_face.set_blendshape(FaceBlendShape.MouthSmileRight, value * 0.7)
        
        s.sendall(py_face.encode())
        time.sleep(0.033)
    
    # Test 5: Animation complexe
    print("\n5. Animation complexe...")
    for i in range(120):  # 4 secondes
        # Reset
        for j in range(52):
            py_face.set_blendshape(FaceBlendShape(j), 0.0)
        
        t = i / 60.0  # Temps en secondes
        
        # Respiration
        breathing = 0.1 * np.sin(t * np.pi * 0.5)
        if breathing > 0:
            py_face.set_blendshape(FaceBlendShape.JawOpen, breathing)
        
        # Clignements périodiques
        if i % 90 < 5:  # Cligner toutes les 3 secondes
            blink = np.sin((i % 5) / 5.0 * np.pi)
            py_face.set_blendshape(FaceBlendShape.EyeBlinkLeft, blink)
            py_face.set_blendshape(FaceBlendShape.EyeBlinkRight, blink)
        
        # Micro-sourire
        smile = 0.2 * (1 + np.sin(t * np.pi * 0.2))
        py_face.set_blendshape(FaceBlendShape.MouthSmileLeft, smile)
        py_face.set_blendshape(FaceBlendShape.MouthSmileRight, smile)
        
        # Sourcils
        brow = 0.1 * np.sin(t * np.pi * 0.3)
        if brow > 0:
            py_face.set_blendshape(FaceBlendShape.BrowInnerUp, brow)
        
        s.sendall(py_face.encode())
        
        if i % 30 == 0:
            print(f"  Temps: {t:.1f}s")
        
        time.sleep(0.033)
    
    # Reset final
    print("\n6. Reset final...")
    for j in range(52):
        py_face.set_blendshape(FaceBlendShape(j), 0.0)
    s.sendall(py_face.encode())
    
    s.close()
    print("\nTest terminé!")


if __name__ == "__main__":
    test_final()