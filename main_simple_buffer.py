#!/usr/bin/env python3
"""
Gala v1 - Application simplifiée
Envoie les données audio par chunks au système de buffer
"""

import asyncio
import logging
import requests
import numpy as np
import io
import wave
import time
from typing import Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GalaAudioSender:
    """Envoie l'audio par chunks au système de buffer"""
    
    def __init__(self):
        self.api_url = "http://localhost:6969"
        self.sample_rate = 16000
        self.chunk_duration_ms = 32  # Envoyer par chunks de 32ms
        self.chunk_size = int(self.sample_rate * self.chunk_duration_ms / 1000 * 2)  # *2 pour 16-bit
        
    def check_api_health(self):
        """Vérifie que l'API est accessible"""
        try:
            response = requests.get(f"{self.api_url}/health")
            if response.status_code == 200:
                health = response.json()
                logger.info(f"API status: {health['status']}")
                logger.info(f"Buffer: {health['buffer_level']}/{health['buffer_max']} bytes")
                return True
            return False
        except Exception as e:
            logger.error(f"Erreur connexion API: {e}")
            return False
    
    def send_audio_chunk(self, audio_data: bytes) -> bool:
        """Envoie un chunk audio à l'API"""
        try:
            response = requests.post(
                f"{self.api_url}/audio_to_blendshapes",
                data=audio_data,
                headers={'Content-Type': 'audio/pcm'}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['buffer_level'] % 10000 < self.chunk_size:  # Log occasionnel
                    logger.debug(f"Buffer: {data['buffer_level']} bytes")
                return True
            else:
                logger.error(f"Erreur API: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur envoi: {e}")
            return False
    
    def generate_test_audio(self, duration: float = 5.0):
        """Génère un audio de test simulant la parole"""
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples)
        
        # Voix avec modulation
        frequency = 150  # Fréquence fondamentale
        audio = 0.5 * np.sin(2 * np.pi * frequency * t)
        
        # Ajouter des harmoniques
        audio += 0.3 * np.sin(2 * np.pi * frequency * 2 * t)
        audio += 0.1 * np.sin(2 * np.pi * frequency * 3 * t)
        
        # Modulation pour simuler la parole
        mod_freq = 5  # Hz - rythme de la parole
        modulation = 0.3 * np.sin(2 * np.pi * mod_freq * t) + 0.7
        audio *= modulation
        
        # Convertir en PCM 16-bit
        audio_int16 = (audio * 16000).astype(np.int16)
        return audio_int16.tobytes()
    
    async def stream_audio(self, audio_data: bytes):
        """Stream l'audio par chunks au système de buffer"""
        total_chunks = len(audio_data) // self.chunk_size
        
        logger.info(f"Streaming {len(audio_data)} bytes en {total_chunks} chunks")
        
        for i in range(0, len(audio_data), self.chunk_size):
            chunk = audio_data[i:i + self.chunk_size]
            
            # Envoyer le chunk
            if not self.send_audio_chunk(chunk):
                logger.error(f"Échec envoi chunk {i//self.chunk_size}")
            
            # Timing pour simuler le temps réel (32ms entre chunks)
            await asyncio.sleep(self.chunk_duration_ms / 1000)
        
        # Flush le buffer à la fin
        try:
            response = requests.post(f"{self.api_url}/flush_buffer")
            logger.info("Buffer flush demandé")
        except:
            pass

async def main():
    """Point d'entrée principal"""
    logger.info("=== Gala Audio Sender - Buffer System ===")
    
    sender = GalaAudioSender()
    
    # Vérifier l'API
    if not sender.check_api_health():
        logger.error("API non accessible")
        return
    
    # Générer et envoyer de l'audio de test
    logger.info("Génération audio de test (5 secondes)")
    test_audio = sender.generate_test_audio(duration=5.0)
    
    # Streamer l'audio
    await sender.stream_audio(test_audio)
    
    # Attendre un peu pour voir les résultats
    await asyncio.sleep(2)
    
    # Vérifier l'état final
    sender.check_api_health()
    
    logger.info("=== Test terminé ===")

if __name__ == "__main__":
    asyncio.run(main())