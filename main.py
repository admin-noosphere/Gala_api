#!/usr/bin/env python3
"""
Gala v1 - Main Application
Utilise l'API unifiée pour la conversion Audio → STT → LLM → TTS → Blendshapes → LiveLink
"""

import asyncio
import logging
import os
import sys
import time
import requests
import numpy as np
import io
from typing import Optional, Dict, Any
from dataclasses import dataclass
import json
import wave

# Import des services externes
import openai

from elevenlabs import generate, Voice, VoiceSettings

# Import de la configuration
from config import config

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class GalaAgent:
    """Agent conversationnel Gala le pirate"""
    
    name: str = "Gala"
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # ID ElevenLabs pour la voix
    personality: str = """
    Tu es Gala, un pirate digital charismatique naviguant dans les océans de données.
    Tu parles avec un accent pirate léger et tu es toujours enthousiaste à l'idée de nouvelles aventures.
    Tu aimes raconter des histoires de tes voyages dans le cyberspace et tu es toujours prêt à aider.
    Tu utilises des expressions pirates comme "Ohé moussaillon!", "Par Neptune!", "Mille sabords!" etc.
    """
    
    conversation_history: list = None
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = [
                {"role": "system", "content": self.personality}
            ]

class GalaConversation:
    """Gère la conversation complète avec Gala"""
    
    def __init__(self):
        self.agent = GalaAgent()
        self.api_base_url = f"http://localhost:{config.api.port}"
        
        # Initialiser les clients
        self.init_clients()
        
    def init_clients(self):
        """Initialise les clients pour STT, LLM et TTS"""
        # OpenAI pour STT et LLM
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            logger.error("OPENAI_API_KEY non définie")
            sys.exit(1)
            
        # ElevenLabs pour TTS (optionnel, peut utiliser OpenAI TTS)
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        if not self.elevenlabs_api_key:
            logger.warning("ELEVENLABS_API_KEY non définie, utilisation d'OpenAI TTS")
            
        logger.info("Clients initialisés")
        
    async def speech_to_text(self, audio_data: bytes) -> str:
        """Convertit l'audio en texte avec OpenAI Whisper"""
        try:
            # Créer un fichier temporaire pour l'audio
            with io.BytesIO(audio_data) as audio_file:
                audio_file.name = "audio.wav"
                audio_file.seek(0)
                
                # Utiliser OpenAI Whisper
                response = openai.Audio.transcribe(
                    model="whisper-1",
                    file=audio_file,
                    language="fr"
                )
                
                return response.text
                
        except Exception as e:
            logger.error(f"Erreur STT: {e}")
            return ""
            
    async def generate_response(self, user_input: str) -> str:
        """Génère une réponse avec le LLM"""
        try:
            # Ajouter le message utilisateur à l'historique
            self.agent.conversation_history.append({"role": "user", "content": user_input})
            
            # Appeler GPT
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=self.agent.conversation_history,
                temperature=0.7,
                max_tokens=150
            )
            
            assistant_message = response.choices[0].message.content
            
            # Ajouter la réponse à l'historique
            self.agent.conversation_history.append({"role": "assistant", "content": assistant_message})
            
            return assistant_message
            
        except Exception as e:
            logger.error(f"Erreur LLM: {e}")
            return "Ohé moussaillon, j'ai un problème avec ma boussole magique!"
            
    async def text_to_speech(self, text: str) -> bytes:
        """Convertit le texte en audio"""
        try:
            if self.elevenlabs_api_key:
                # Utiliser ElevenLabs
                audio = generate(
                    text=text,
                    voice=Voice(
                        voice_id=self.agent.voice_id,
                        settings=VoiceSettings(
                            stability=0.5,
                            similarity_boost=0.75,
                            style=0.0,
                            use_speaker_boost=True
                        )
                    ),
                    api_key=self.elevenlabs_api_key
                )
                return audio
            else:
                # Utiliser OpenAI TTS
                response = openai.Audio.create(
                    model="tts-1",
                    voice="onyx",
                    input=text
                )
                return response.content
                
        except Exception as e:
            logger.error(f"Erreur TTS: {e}")
            # Générer un audio silencieux en cas d'erreur
            return self._generate_silence()
            
    def _generate_silence(self, duration: float = 0.5) -> bytes:
        """Génère un audio silencieux"""
        sample_rate = config.audio.sample_rate
        num_samples = int(sample_rate * duration)
        silence = np.zeros(num_samples, dtype=np.int16)
        
        # Créer un fichier WAV en mémoire
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(silence.tobytes())
            
        return buffer.getvalue()
        
    async def send_to_blendshapes(self, audio_data: bytes) -> Dict[str, Any]:
        """Envoie l'audio à l'API unifiée pour conversion en blendshapes"""
        try:
            response = requests.post(
                f"{self.api_base_url}/audio_to_blendshapes",
                data=audio_data,
                headers={'Content-Type': 'audio/wav'}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erreur API blendshapes: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Erreur envoi blendshapes: {e}")
            return None
            
    async def process_conversation(self, user_audio: bytes):
        """Traite un cycle complet de conversation"""
        try:
            # 1. STT - Convertir l'audio en texte
            logger.info("Conversion audio → texte...")
            user_text = await self.speech_to_text(user_audio)
            logger.info(f"Utilisateur: {user_text}")
            
            if not user_text:
                return
                
            # 2. LLM - Générer une réponse
            logger.info("Génération de la réponse...")
            response_text = await self.generate_response(user_text)
            logger.info(f"Gala: {response_text}")
            
            # 3. TTS - Convertir la réponse en audio
            logger.info("Conversion texte → audio...")
            response_audio = await self.text_to_speech(response_text)
            
            # 4. Blendshapes - Envoyer l'audio à l'API pour animation
            logger.info("Envoi audio → blendshapes → LiveLink...")
            blendshapes_result = await self.send_to_blendshapes(response_audio)
            
            if blendshapes_result:
                logger.info(f"Blendshapes générés: {len(blendshapes_result['blendshapes'])} valeurs")
                logger.info(f"FPS: {blendshapes_result['fps']}")
            else:
                logger.error("Échec de la génération des blendshapes")
                
        except Exception as e:
            logger.error(f"Erreur dans le cycle de conversation: {e}")

async def main():
    """Point d'entrée principal"""
    logger.info("=== Démarrage de Gala v1 ===")
    
    # Vérifier que l'API unifiée est en cours d'exécution
    try:
        response = requests.get(f"http://localhost:{config.api.port}/health")
        if response.status_code != 200:
            logger.error("L'API unifiée n'est pas accessible")
            logger.info("Lancez d'abord: python api_client.py")
            return
    except:
        logger.error("Impossible de se connecter à l'API unifiée")
        logger.info("Lancez d'abord: python api_client.py")
        return
        
    # Créer l'instance de conversation
    conversation = GalaConversation()
    
    # Message de bienvenue
    welcome_text = "Ohé moussaillon! C'est moi, Gala le pirate digital! Prêt pour l'aventure?"
    logger.info(f"Gala: {welcome_text}")
    
    # Convertir et envoyer le message de bienvenue
    welcome_audio = await conversation.text_to_speech(welcome_text)
    await conversation.send_to_blendshapes(welcome_audio)
    
    logger.info("Gala est prêt! En attente d'audio...")
    
    # Boucle principale (pour les tests)
    # Dans une vraie application, ceci serait remplacé par un serveur websocket ou HTTP
    while True:
        try:
            # Simuler la réception d'audio (remplacer par une vraie source audio)
            logger.info("En attente d'audio utilisateur...")
            await asyncio.sleep(5)
            
            # Pour les tests: générer un audio de test
            test_audio = conversation._generate_silence(1.0)
            
            # Traiter la conversation
            await conversation.process_conversation(test_audio)
            
        except KeyboardInterrupt:
            logger.info("Arrêt demandé...")
            break
        except Exception as e:
            logger.error(f"Erreur dans la boucle principale: {e}")
            await asyncio.sleep(1)
            
    logger.info("=== Arrêt de Gala v1 ===")

if __name__ == "__main__":
    asyncio.run(main())