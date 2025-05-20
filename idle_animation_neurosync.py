#!/usr/bin/env python3
"""
Animation idle style NeuroSync_Player pour Gala v1
Utilise PyLiveLinkFace pour envoyer des animations naturelles
"""

import time
import socket
import threading
from modules.livelink_neurosync import LiveLinkNeuroSync, FaceBlendShape
from modules.pylivelinkface import PyLiveLinkFace
import numpy as np


class IdleAnimation:
    """Gestionnaire d'animation idle compatible NeuroSync_Player"""
    
    def __init__(self, udp_ip: str = "192.168.1.14", udp_port: int = 11111, fps: int = 60):
        self.udp_ip = udp_ip
        self.udp_port = udp_port
        self.fps = fps
        
        # Client LiveLink
        self.livelink = LiveLinkNeuroSync(udp_ip=udp_ip, udp_port=udp_port, fps=fps)
        
        # État de l'animation
        self.running = False
        self.current_frame = 0
        self.animation_thread = None
        
        # Données d'animation idle par défaut
        self.default_animation_data = self._create_default_animation()
        
    def _create_default_animation(self):
        """
        Crée une animation idle de base
        120 frames (2 secondes à 60 FPS) en boucle
        """
        frames = []
        total_frames = 120
        
        for i in range(total_frames):
            blendshapes = [0.0] * 61  # LiveLink utilise 61 valeurs
            
            # Respiration
            breathing_phase = (i / total_frames) * 2 * np.pi
            jaw_value = 0.02 * np.sin(breathing_phase)
            blendshapes[17] = max(0, jaw_value)  # JawOpen
            
            # Micro-mouvements des narines
            nose_value = 0.01 * np.sin(breathing_phase + np.pi/4)
            blendshapes[49] = max(0, nose_value)  # NoseSneerLeft
            blendshapes[50] = max(0, nose_value)  # NoseSneerRight
            
            # Clignements (toutes les 3-5 secondes)
            blink_cycle = 180 + int(60 * np.sin(i * 0.01))  # Cycle variable
            if (i % blink_cycle) < 6:
                blink_progress = (i % blink_cycle) / 6
                blink_value = np.sin(blink_progress * np.pi)
                blendshapes[0] = blink_value  # EyeBlinkLeft
                blendshapes[7] = blink_value  # EyeBlinkRight
            
            # Micro-mouvements des sourcils
            brow_phase = (i / total_frames) * np.pi
            brow_value = 0.015 * np.sin(brow_phase * 0.5)
            blendshapes[43] = max(0, brow_value)  # BrowInnerUp
            
            # Micro-expressions
            if i > 60 and i < 90:  # Léger sourire au milieu du cycle
                smile_progress = (i - 60) / 30
                smile_value = 0.1 * np.sin(smile_progress * np.pi)
                blendshapes[23] = smile_value  # MouthSmileLeft
                blendshapes[24] = smile_value  # MouthSmileRight
            
            frames.append(blendshapes)
        
        return frames
    
    def start(self):
        """Démarre l'animation idle en arrière-plan"""
        if not self.running:
            self.running = True
            self.animation_thread = threading.Thread(target=self._animation_loop)
            self.animation_thread.start()
            print(f"Animation idle démarrée ({self.udp_ip}:{self.udp_port})")
    
    def stop(self):
        """Arrête l'animation idle"""
        if self.running:
            self.running = False
            if self.animation_thread:
                self.animation_thread.join()
            # Envoyer position neutre
            self.livelink.reset()
            self.livelink.send_current()
            print("Animation idle arrêtée")
    
    def _animation_loop(self):
        """Boucle principale d'animation"""
        frame_duration = 1.0 / self.fps
        
        while self.running:
            start_time = time.time()
            
            # Obtenir la frame actuelle de l'animation
            frame_data = self.default_animation_data[self.current_frame]
            
            # Envoyer les blendshapes
            self.livelink.send_blendshapes_direct(frame_data)
            
            # Incrémenter l'index de frame
            self.current_frame = (self.current_frame + 1) % len(self.default_animation_data)
            
            # Maintenir le FPS
            elapsed = time.time() - start_time
            if elapsed < frame_duration:
                time.sleep(frame_duration - elapsed)
    
    def blend_to_facial_data(self, facial_data: list, blend_duration: float = 0.5):
        """
        Blend de l'idle vers des données faciales spécifiques
        
        Args:
            facial_data: Liste de blendshapes cibles
            blend_duration: Durée du blend en secondes
        """
        blend_frames = int(blend_duration * self.fps)
        
        # Frame de départ (idle actuelle)
        start_frame = self.default_animation_data[self.current_frame]
        
        for i in range(blend_frames):
            weight = i / blend_frames
            blended_frame = []
            
            # Blend linéaire entre idle et cible
            for j in range(61):
                start_val = start_frame[j]
                target_val = facial_data[j] if j < len(facial_data) else 0.0
                blended_val = (1 - weight) * start_val + weight * target_val
                blended_frame.append(blended_val)
            
            self.livelink.send_blendshapes_direct(blended_frame)
            time.sleep(1 / self.fps)
    
    def blend_back_to_idle(self, blend_duration: float = 0.5):
        """Retour progressif à l'animation idle"""
        # Obtenir les valeurs actuelles
        current_values = self.livelink.py_face.get_blendshapes()
        
        blend_frames = int(blend_duration * self.fps)
        target_frame_idx = 0  # Toujours revenir au début de l'idle
        
        for i in range(blend_frames):
            weight = i / blend_frames
            blended_frame = []
            
            # Blend vers l'idle
            target_frame = self.default_animation_data[target_frame_idx]
            
            for j in range(61):
                current_val = current_values[j]
                target_val = target_frame[j]
                blended_val = (1 - weight) * current_val + weight * target_val
                blended_frame.append(blended_val)
            
            self.livelink.send_blendshapes_direct(blended_frame)
            time.sleep(1 / self.fps)
        
        # Reprendre l'animation idle normale
        self.current_frame = target_frame_idx


def main():
    """Test de l'animation idle"""
    print("=== Test Animation Idle NeuroSync ===")
    
    # Créer l'animation idle
    idle = IdleAnimation(udp_ip="192.168.1.14", udp_port=11111)
    
    try:
        # Démarrer l'animation
        idle.start()
        
        print("Animation idle en cours...")
        print("Appuyez sur Ctrl+C pour arrêter")
        
        # Laisser tourner
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nArrêt...")
        idle.stop()
        idle.livelink.close()


if __name__ == "__main__":
    main()