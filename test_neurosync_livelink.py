#!/usr/bin/env python3
"""
Test de connexion LiveLink avec l'approche NeuroSync_Player
Utilise PyLiveLinkFace pour une compatibilité maximale
"""

import time
import numpy as np
from modules.livelink_neurosync import LiveLinkNeuroSync, FaceBlendShape
from modules.pylivelinkface import PyLiveLinkFace

# Configuration
LIVELINK_IP = "192.168.1.14"  # IP d'Unreal Engine
LIVELINK_PORT = 11111


def test_basic_connection():
    """Test basique de connexion"""
    print("=== Test de connexion basique ===")
    
    livelink = LiveLinkNeuroSync(udp_ip=LIVELINK_IP, udp_port=LIVELINK_PORT)
    print(f"Connexion établie vers {LIVELINK_IP}:{LIVELINK_PORT}")
    
    # Position neutre
    print("Envoi position neutre...")
    livelink.reset()
    livelink.send_current()
    time.sleep(1)
    
    # Test simple - ouverture de la mâchoire
    print("Test ouverture de la mâchoire...")
    for i in range(30):
        livelink.reset()
        value = i / 30.0
        livelink.set_blendshape(FaceBlendShape.JawOpen, value)
        livelink.send_current()
        time.sleep(0.033)  # 30 FPS
    
    # Retour position neutre
    livelink.reset()
    livelink.send_current()
    livelink.close()
    print("Test basique terminé\n")


def test_idle_animation():
    """Test d'animation idle style NeuroSync_Player"""
    print("=== Test animation idle ===")
    
    livelink = LiveLinkNeuroSync(udp_ip=LIVELINK_IP, udp_port=LIVELINK_PORT)
    print("Démarrage de l'animation idle...")
    
    frame_count = 0
    fps = 60
    duration = 10  # 10 secondes
    
    try:
        while frame_count < duration * fps:
            # Reset des valeurs
            livelink.reset()
            
            # Respiration
            breathing_phase = (frame_count / fps) * 0.5 * np.pi
            jaw_breathing = 0.03 * np.sin(breathing_phase)
            livelink.set_blendshape(FaceBlendShape.JawOpen, max(0, jaw_breathing))
            
            # Clignements périodiques
            if frame_count % (fps * 3) < 6:  # Cligner toutes les 3 secondes
                blink_value = np.sin((frame_count % 6) / 6 * np.pi)
                livelink.set_blendshape(FaceBlendShape.EyeBlinkLeft, blink_value)
                livelink.set_blendshape(FaceBlendShape.EyeBlinkRight, blink_value)
            
            # Micro-mouvements des sourcils
            brow_phase = (frame_count / fps) * 0.3 * np.pi
            brow_value = 0.02 * np.sin(brow_phase)
            livelink.set_blendshape(FaceBlendShape.BrowInnerUp, max(0, brow_value))
            
            # Micro-sourire
            if (frame_count // fps) % 5 == 0:  # Sourire toutes les 5 secondes
                smile_phase = ((frame_count % fps) / fps) * np.pi
                if smile_phase < np.pi:
                    smile_value = 0.1 * np.sin(smile_phase)
                    livelink.set_blendshape(FaceBlendShape.MouthSmileLeft, smile_value)
                    livelink.set_blendshape(FaceBlendShape.MouthSmileRight, smile_value)
            
            # Envoyer les données
            livelink.send_current()
            
            # Affichage debug toutes les secondes
            if frame_count % fps == 0:
                print(f"Frame {frame_count}: Animation idle en cours...")
            
            frame_count += 1
            time.sleep(1 / fps)
    
    except KeyboardInterrupt:
        print("\nArrêt de l'animation...")
    
    finally:
        livelink.reset()
        livelink.send_current()
        livelink.close()
    
    print("Animation idle terminée\n")


def test_68_to_61_conversion():
    """Test la conversion des 68 blendshapes ARKit vers 61 LiveLink"""
    print("=== Test conversion ARKit → LiveLink ===")
    
    livelink = LiveLinkNeuroSync(udp_ip=LIVELINK_IP, udp_port=LIVELINK_PORT)
    
    # Créer des données de test (68 valeurs ARKit)
    arkit_values = [0.0] * 68
    
    # Quelques valeurs de test
    arkit_values[0] = 0.5   # EyeBlink_L
    arkit_values[17] = 0.7  # JawOpen
    arkit_values[23] = 0.3  # MouthSmile_L
    arkit_values[54] = 0.5  # EyeBlinkLeft (duplicate)
    
    print("Valeurs ARKit de test:")
    print(f"  EyeBlink_L (0): {arkit_values[0]}")
    print(f"  JawOpen (17): {arkit_values[17]}")
    print(f"  MouthSmile_L (23): {arkit_values[23]}")
    print(f"  EyeBlinkLeft dup (54): {arkit_values[54]}")
    
    # Envoyer les valeurs
    livelink.send_blendshapes(arkit_values)
    time.sleep(0.5)
    
    livelink.close()
    print("Test de conversion terminé\n")


def test_direct_livelink():
    """Test avec des valeurs LiveLink directes (61 valeurs)"""
    print("=== Test LiveLink direct (61 valeurs) ===")
    
    livelink = LiveLinkNeuroSync(udp_ip=LIVELINK_IP, udp_port=LIVELINK_PORT)
    
    # Animation de test
    for i in range(60):
        values = [0.0] * 61
        
        # Bouche ouverte progressivement
        values[17] = i / 60.0  # JawOpen
        
        # Sourcils levés
        values[43] = 0.5 * np.sin(i * 0.1)  # BrowInnerUp
        
        # Sourire
        values[23] = 0.3  # MouthSmileLeft
        values[24] = 0.3  # MouthSmileRight
        
        livelink.send_blendshapes_direct(values)
        time.sleep(0.033)
    
    # Retour à neutre
    livelink.reset()
    livelink.send_current()
    livelink.close()
    print("Test direct terminé\n")


def main():
    """Programme principal"""
    print("=== Test LiveLink style NeuroSync_Player ===")
    print(f"IP cible: {LIVELINK_IP}")
    print(f"Port: {LIVELINK_PORT}")
    print()
    
    tests = [
        ("Connection basique", test_basic_connection),
        ("Animation idle", test_idle_animation),
        ("Conversion ARKit → LiveLink", test_68_to_61_conversion),
        ("LiveLink direct", test_direct_livelink)
    ]
    
    for i, (test_name, test_func) in enumerate(tests):
        print(f"\n[{i+1}/{len(tests)}] {test_name}")
        print("-" * 40)
        try:
            test_func()
        except Exception as e:
            print(f"Erreur: {e}")
        time.sleep(1)
    
    print("\n=== Tests terminés ===")


if __name__ == "__main__":
    main()