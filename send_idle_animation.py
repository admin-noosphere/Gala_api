#!/usr/bin/env python3
"""
Envoie une animation idle en continu à Unreal Engine via LiveLink
Similaire à la default_animation_loop de NeuroSync_Player
"""

import asyncio
import time
import numpy as np
from modules.livelink_client import LiveLinkClient
from config import CONFIG

class IdleAnimationSender:
    """Gestionnaire d'animation idle pour LiveLink"""
    
    def __init__(self, livelink_client: LiveLinkClient):
        self.client = livelink_client
        self.running = False
        self.frame_index = 0
        self.total_frames = 120  # Cycle de 2 secondes à 60 FPS
        
    def create_idle_animation(self) -> list:
        """
        Crée une animation idle naturelle avec:
        - Respiration subtile
        - Clignements périodiques
        - Micro-mouvements faciaux
        """
        blendshapes = [0.0] * 68
        
        # Phase de respiration (cycle de 2 secondes)
        breathing_phase = (self.frame_index / self.total_frames) * 2 * np.pi
        
        # Respiration via JawOpen très subtile
        jaw_breathing = 0.03 * np.sin(breathing_phase)
        blendshapes[17] = max(0, jaw_breathing)  # JawOpen
        
        # Respiration via les narines
        nose_breathing = 0.02 * np.sin(breathing_phase + np.pi/4)
        blendshapes[49] = max(0, nose_breathing)  # NoseSneer_L
        blendshapes[50] = max(0, nose_breathing)  # NoseSneer_R
        
        # Respiration via la poitrine (CheekPuff peut simuler)
        chest_breathing = 0.01 * np.sin(breathing_phase)
        blendshapes[46] = max(0, chest_breathing)  # CheekPuff
        
        # Clignements naturels
        self._add_blinks(blendshapes)
        
        # Micro-mouvements des yeux
        self._add_eye_movements(blendshapes)
        
        # Micro-expressions
        self._add_micro_expressions(blendshapes)
        
        # Mouvements subtils de la tête
        self._add_head_movements(blendshapes)
        
        return blendshapes
    
    def _add_blinks(self, blendshapes: list):
        """Ajoute des clignements naturels"""
        # Clignement principal toutes les 3-5 secondes
        blink_intervals = [180, 240, 300, 360]  # Intervalles variés
        current_interval = blink_intervals[self.frame_index // 1000 % len(blink_intervals)]
        
        blink_duration = 6  # ~100ms à 60 FPS
        
        if (self.frame_index % current_interval) < blink_duration:
            progress = (self.frame_index % current_interval) / blink_duration
            # Courbe de clignement naturelle (rapide fermeture, ouverture plus lente)
            if progress < 0.3:
                blink_value = progress / 0.3
            else:
                blink_value = 1.0 - (progress - 0.3) / 0.7
            
            blendshapes[0] = blink_value  # EyeBlink_L
            blendshapes[1] = blink_value  # EyeBlink_R
    
    def _add_eye_movements(self, blendshapes: list):
        """Ajoute des micro-mouvements oculaires"""
        # Saccades subtiles
        saccade_phase = self.frame_index * 0.01
        
        # Mouvements horizontaux
        look_h = 0.05 * np.sin(saccade_phase)
        if look_h > 0:
            blendshapes[6] = look_h  # EyeLookOut_L
            blendshapes[5] = look_h  # EyeLookIn_R
        else:
            blendshapes[5] = -look_h  # EyeLookIn_L
            blendshapes[7] = -look_h  # EyeLookOut_R
        
        # Mouvements verticaux plus subtils
        look_v = 0.03 * np.sin(saccade_phase * 0.7 + np.pi/3)
        if look_v > 0:
            blendshapes[8] = look_v  # EyeLookUp_L
            blendshapes[9] = look_v  # EyeLookUp_R
        else:
            blendshapes[2] = -look_v  # EyeLookDown_L
            blendshapes[3] = -look_v  # EyeLookDown_R
    
    def _add_micro_expressions(self, blendshapes: list):
        """Ajoute des micro-expressions faciales"""
        # Micro-sourire occasionnel
        smile_phase = self.frame_index * 0.003
        smile_value = max(0, 0.05 * np.sin(smile_phase) * (1 + 0.5 * np.sin(smile_phase * 0.3)))
        
        blendshapes[23] = smile_value  # MouthSmile_L
        blendshapes[24] = smile_value  # MouthSmile_R
        
        # Légère tension des sourcils (concentration)
        brow_phase = self.frame_index * 0.002
        brow_inner = 0.02 * np.sin(brow_phase)
        blendshapes[44] = max(0, brow_inner)  # BrowInnerUp
        
        # Léger plissement des yeux (squint)
        squint_value = 0.01 * np.sin(brow_phase + np.pi/2)
        blendshapes[10] = max(0, squint_value)  # EyeSquint_L
        blendshapes[11] = max(0, squint_value)  # EyeSquint_R
    
    def _add_head_movements(self, blendshapes: list):
        """Ajoute des mouvements subtils de la tête"""
        # Oscillation très légère
        head_phase = self.frame_index * 0.001
        
        # Rotation horizontale (yaw)
        blendshapes[52] = 0.02 * np.sin(head_phase)  # HeadYaw
        
        # Inclinaison verticale (pitch)
        blendshapes[53] = 0.015 * np.sin(head_phase * 0.8 + np.pi/4)  # HeadPitch
        
        # Roulis latéral (roll)
        blendshapes[54] = 0.01 * np.sin(head_phase * 0.6 + np.pi/2)  # HeadRoll
    
    async def start(self):
        """Démarre l'envoi de l'animation idle"""
        self.running = True
        frame_duration = 1.0 / CONFIG["target_fps"]
        
        print("Démarrage de l'animation idle...")
        print("Appuyez sur Ctrl+C pour arrêter")
        
        try:
            while self.running:
                start_time = time.time()
                
                # Créer et envoyer les blendshapes
                blendshapes = self.create_idle_animation()
                await self.client.send_blendshapes(blendshapes)
                
                # Debug toutes les secondes
                if self.frame_index % CONFIG["target_fps"] == 0:
                    print(f"Frame {self.frame_index}: Animation idle en cours...")
                    print(f"  Respiration (JawOpen): {blendshapes[17]:.3f}")
                    print(f"  Clignement (EyeBlink_L): {blendshapes[0]:.3f}")
                    print(f"  Sourire (MouthSmile_L): {blendshapes[23]:.3f}")
                
                # Incrémenter l'index
                self.frame_index = (self.frame_index + 1) % (CONFIG["target_fps"] * 60)  # Reset après 1 minute
                
                # Maintenir le FPS
                elapsed = time.time() - start_time
                if elapsed < frame_duration:
                    await asyncio.sleep(frame_duration - elapsed)
                    
        except KeyboardInterrupt:
            print("\nArrêt de l'animation...")
            self.running = False
    
    def stop(self):
        """Arrête l'animation"""
        self.running = False

async def main():
    """Programme principal"""
    print("=== Animation Idle LiveLink ===")
    print(f"Configuration:")
    print(f"  IP: {CONFIG['livelink_ip']}")
    print(f"  Port: {CONFIG['livelink_port']}")
    print(f"  FPS: {CONFIG['target_fps']}")
    print()
    
    # Initialiser le client LiveLink
    client = LiveLinkClient(
        host=CONFIG["livelink_ip"],
        port=CONFIG["livelink_port"],
        fps=CONFIG["target_fps"]
    )
    
    # Tenter une connexion WebSocket d'abord
    try:
        await client.connect_websocket()
        if client.is_connected:
            print("✓ Connexion WebSocket établie")
        else:
            print("WebSocket indisponible, utilisation d'UDP")
    except Exception as e:
        print(f"WebSocket indisponible: {e}")
        print("Utilisation d'UDP")
    
    # Créer et démarrer l'animation
    animator = IdleAnimationSender(client)
    
    try:
        await animator.start()
    finally:
        await client.aclose()
        print("Connexion fermée.")

if __name__ == "__main__":
    asyncio.run(main())