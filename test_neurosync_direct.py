#!/usr/bin/env python3
"""
Test de connexion LiveLink en utilisant l'approche exacte de wave_to_face.py
Utilise un socket direct et pylivelinkface comme dans NeuroSync_Player
"""

import socket
import time
import numpy as np
from modules.pylivelinkface import PyLiveLinkFace, FaceBlendShape

# Configuration
UDP_IP = "192.168.1.14"
UDP_PORT = 11111


def create_socket_connection():
    """Crée une connexion socket comme dans wave_to_face.py"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((UDP_IP, UDP_PORT))
    return s


def initialize_py_face():
    """Initialise PyLiveLinkFace comme dans wave_to_face.py"""
    py_face = PyLiveLinkFace()
    # Initialiser seulement les blendshapes valides (0-51)
    for i in range(52):  # 0-51 pour notre FaceBlendShape
        py_face.set_blendshape(FaceBlendShape(i), 0.0)
    return py_face


def test_basic_connection():
    """Test de base avec approche NeuroSync_Player"""
    print("=== Test connexion directe (style wave_to_face.py) ===")
    
    # Initialisation
    py_face = initialize_py_face()
    socket_connection = create_socket_connection()
    
    print(f"Connexion établie vers {UDP_IP}:{UDP_PORT}")
    
    try:
        # Position neutre
        print("Envoi position neutre...")
        socket_connection.sendall(py_face.encode())
        time.sleep(1)
        
        # Test ouverture mâchoire
        print("Test ouverture de la mâchoire...")
        for i in range(30):
            # Reset tous les blendshapes
            for j in range(52):  # Seulement 0-51
                py_face.set_blendshape(FaceBlendShape(j), 0.0)
            
            # Set jaw open
            value = i / 30.0
            py_face.set_blendshape(FaceBlendShape.JawOpen, value)
            
            # Envoyer
            try:
                socket_connection.sendall(py_face.encode())
            except Exception as e:
                print(f"Erreur envoi: {e}")
            
            time.sleep(0.033)  # 30 FPS
        
        # Retour position neutre
        for j in range(52):
            py_face.set_blendshape(FaceBlendShape(j), 0.0)
        socket_connection.sendall(py_face.encode())
        
    finally:
        socket_connection.close()
    
    print("Test terminé\n")


def test_idle_animation():
    """Test animation idle style NeuroSync_Player"""
    print("=== Test animation idle (style wave_to_face.py) ===")
    
    py_face = initialize_py_face()
    socket_connection = create_socket_connection()
    
    frame_count = 0
    fps = 60
    duration = 10  # 10 secondes
    
    try:
        while frame_count < duration * fps:
            # Reset
            for j in range(52):
                py_face.set_blendshape(FaceBlendShape(j), 0.0)
            
            # Respiration
            breathing_phase = (frame_count / fps) * 0.5 * np.pi
            jaw_breathing = 0.03 * np.sin(breathing_phase)
            if jaw_breathing > 0:
                py_face.set_blendshape(FaceBlendShape.JawOpen, jaw_breathing)
            
            # Clignements périodiques
            if frame_count % (fps * 3) < 6:  # Cligner toutes les 3 secondes
                blink_value = np.sin((frame_count % 6) / 6 * np.pi)
                py_face.set_blendshape(FaceBlendShape.EyeBlinkLeft, blink_value)
                py_face.set_blendshape(FaceBlendShape.EyeBlinkRight, blink_value)
            
            # Micro-mouvements des sourcils
            brow_phase = (frame_count / fps) * 0.3 * np.pi
            brow_value = 0.02 * np.sin(brow_phase)
            if brow_value > 0:
                py_face.set_blendshape(FaceBlendShape.BrowInnerUp, brow_value)
            
            # Micro-sourire
            if (frame_count // fps) % 5 == 0:  # Sourire toutes les 5 secondes
                smile_phase = ((frame_count % fps) / fps) * np.pi
                if smile_phase < np.pi:
                    smile_value = 0.1 * np.sin(smile_phase)
                    py_face.set_blendshape(FaceBlendShape.MouthSmileLeft, smile_value)
                    py_face.set_blendshape(FaceBlendShape.MouthSmileRight, smile_value)
            
            # Envoyer
            try:
                socket_connection.sendall(py_face.encode())
            except Exception as e:
                print(f"Erreur envoi frame {frame_count}: {e}")
            
            # Debug toutes les secondes
            if frame_count % fps == 0:
                print(f"Frame {frame_count}/{duration * fps}")
            
            frame_count += 1
            time.sleep(1 / fps)
    
    except KeyboardInterrupt:
        print("\nArrêt de l'animation...")
    
    finally:
        # Reset final
        for j in range(52):
            py_face.set_blendshape(FaceBlendShape(j), 0.0)
        socket_connection.sendall(py_face.encode())
        socket_connection.close()
    
    print("Animation terminée\n")


def main():
    """Programme principal"""
    print("=== Test LiveLink Direct (approche wave_to_face.py) ===")
    print(f"IP cible: {UDP_IP}")
    print(f"Port: {UDP_PORT}")
    print()
    
    # Test 1: Connexion basique
    test_basic_connection()
    time.sleep(1)
    
    # Test 2: Animation idle
    test_idle_animation()
    
    print("\n=== Tests terminés ===")


if __name__ == "__main__":
    main()