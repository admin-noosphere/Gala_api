#!/usr/bin/env python3
"""
Version corrigée de main.py avec l'approche LiveLink validée
Utilise le client API NeuroSync qui fonctionne correctement
"""

import asyncio
import itertools
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import google.generativeai as genai
import requests
import wave
from dotenv import load_dotenv
from loguru import logger
from pipecat.frames.frames import (
    BlendshapeFrame,
    TTSAudioRawFrame,
    TTSSpeakFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
    VisemeFrame,
    Frame
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.buffer import TranscriptionQueueBufferService
from pipecat.services.elevenlabs import ElevenLabsTTSService
from pipecat.services.openai import OpenAISTTService, OpenAITTSService
from pipecat.services.google_llm import GoogleGenAILLMService
from pipecat.transports.services.daily import (
    DailyDataTranscriptionSettings,
    DailyParams,
    DailyTranscriptionSettings,
    DailyTransport,
)

# Import corrigé pour utiliser notre approche validée
import socket
import numpy as np
from modules.pylivelinkface import PyLiveLinkFace, FaceBlendShape

# ---------------------------------------------------------------------------
# Configuration du logging
# ---------------------------------------------------------------------------
logging.basicConfig()
logging.getLogger("pipecat").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Client API NeuroSync avec envoi LiveLink direct
# ---------------------------------------------------------------------------
class NeuroSyncApiClient:
    """Client API NeuroSync avec envoi direct LiveLink"""
    
    def __init__(self, host="127.0.0.1", port=6969, livelink_ip="192.168.1.14", livelink_port=11111):
        self.host = host
        self.port = port
        self.api_url = f"http://{host}:{port}"
        self.logger = logging.getLogger(__name__)
        
        # LiveLink setup
        self.livelink_ip = livelink_ip
        self.livelink_port = livelink_port
        self.py_face = PyLiveLinkFace(name="GalaFace", fps=60)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.connect((self.livelink_ip, self.livelink_port))
        self.logger.info(f"LiveLink connecté à {self.livelink_ip}:{self.livelink_port}")
    
    async def send_audio_and_animate(self, audio_data: bytes, sample_rate: int = 16000) -> List[float]:
        """
        Envoie l'audio à l'API et anime directement le personnage
        """
        try:
            # Debug log
            self.logger.info(f"⚡ Envoi audio: {len(audio_data)} octets")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/audio_to_blendshapes",
                    data=audio_data,
                    headers={"Content-Type": "audio/pcm"},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        blendshapes = result.get('blendshapes', [])
                        
                        if blendshapes:
                            self.logger.info(f"✅ Reçu {len(blendshapes)} blendshapes")
                            
                            # Envoyer directement à LiveLink
                            self.send_to_livelink(blendshapes)
                            return blendshapes
                        else:
                            self.logger.error("Pas de blendshapes dans la réponse")
                            return []
                    else:
                        self.logger.error(f"❌ Erreur API: {response.status}")
                        return []
                        
        except Exception as e:
            self.logger.error(f"❌ Erreur: {e}")
            return []
    
    def send_to_livelink(self, blendshapes: List[float]):
        """Envoie directement les blendshapes à Unreal via LiveLink"""
        try:
            # Reset tous les blendshapes
            for i in range(52):  # 0-51 valides
                self.py_face.set_blendshape(FaceBlendShape(i), 0.0)
            
            # Appliquer les nouvelles valeurs
            for i in range(min(52, len(blendshapes))):
                value = float(blendshapes[i])
                # Limiter entre 0 et 1
                value = max(0.0, min(1.0, value))
                self.py_face.set_blendshape(FaceBlendShape(i), value)
            
            # Encoder et envoyer
            data = self.py_face.encode()
            self.socket.sendall(data)
            
        except Exception as e:
            self.logger.error(f"Erreur LiveLink: {e}")
    
    def close(self):
        """Ferme les connexions"""
        if self.socket:
            self.socket.close()

# ---------------------------------------------------------------------------
# Processor NeuroSync avec buffer et animation directe
# ---------------------------------------------------------------------------
class NeuroSyncBufferProcessor(FrameProcessor):
    """Processeur qui bufferise l'audio et anime le personnage"""
    
    def __init__(self, api_client: NeuroSyncApiClient, config=None):
        super().__init__(name="neurosync_buffer")
        self.api_client = api_client
        self.config = config or {}
        self._logger = logging.getLogger(__name__)
        
        # Buffer pour accumulation
        self._buffer = bytearray()
        # Accumule environ 192 ms d'audio (16 kHz mono, 16‑bit)
        self._min_buffer_size = int(16000 * 0.192 * 2)  # 6144 octets
        
    async def process_frame(self, frame, direction=FrameDirection.DOWNSTREAM):
        # Toujours appeler super()
        await super().process_frame(frame, direction)
        
        # Traiter l'audio en aval
        if (
            direction == FrameDirection.DOWNSTREAM 
            and hasattr(frame, "audio") 
            and frame.audio
        ):
            audio_data = frame.audio
            if isinstance(audio_data, bytes) and len(audio_data) > 0:
                # Ajouter au buffer
                self._buffer.extend(audio_data)
                
                # Si buffer suffisant, envoyer
                if len(self._buffer) >= self._min_buffer_size:
                    self._logger.info(f"⚡ Buffer: {len(self._buffer)} octets")
                    
                    # Envoyer à l'API et animer
                    await self.api_client.send_audio_and_animate(
                        bytes(self._buffer), 
                        sample_rate=16000
                    )
                    
                    # Vider le buffer
                    self._buffer.clear()
        
        # Propager le frame
        await self.push_frame(frame, direction)

# ---------------------------------------------------------------------------
# Pipeline principale
# ---------------------------------------------------------------------------

# Chargement des variables d'environnement
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_PATH)

# Variables
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "dbab4e489478bd4338ad6cbb3901a433550d7cf1")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-001")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
DAILY_ROOM_URL = os.getenv("DAILY_ROOM_URL")
DAILY_API_TOKEN = os.getenv("DAILY_API_TOKEN")
BOT_NAME = os.getenv("BOT_NAME", "Gala")
TTS_SERVICE = os.getenv("TTS_SERVICE", "openai").lower()

# Services
stt = OpenAISTTService(
    api_key=OPENAI_API_KEY,
    language="fr"
)

if TTS_SERVICE == "elevenlabs":
    tts = ElevenLabsTTSService(
        api_key=ELEVENLABS_API_KEY,
        model="eleven_turbo_v2",
        language="fr"
    )
else:
    tts = OpenAITTSService(
        api_key=OPENAI_API_KEY,
        voice="nova"
    )

llm = GoogleGenAILLMService(
    api_key=GEMINI_API_KEY,
    model_id=GEMINI_MODEL
)

transport = DailyTransport(
    DAILY_ROOM_URL,
    DAILY_API_TOKEN,
    BOT_NAME,
    DailyParams(
        audio_out_enabled=True,
        transcription_enabled=False,
        vad_enabled=True,
        vad_analyzer=DAILY_VAD,
        use_udp_connections=UDP_CONNECTIONS
    )
)

# Client API NeuroSync avec LiveLink correct
api_client = NeuroSyncApiClient(
    host="127.0.0.1", 
    port=6969,
    livelink_ip="192.168.1.14",  # IP correcte
    livelink_port=11111
)

# Processeur NeuroSync
neurosync_processor = NeuroSyncBufferProcessor(api_client)

# Messages système
messages = [
    {
        "role": "system",
        "content": """Tu es Gala, une femme pirate IA. Tu es le capitaine de ton navire.
Tu parles toujours en français avec l'accent et l'attitude typique d'un pirate.
Sois fière, audacieuse et aventureuse. Tu es toujours prête pour l'action."""
    }
]

context = OpenAILLMContext(messages)
context_agg = llm.create_context_aggregator(context)

# Pipeline
pipeline = Pipeline([
    transport.input(),
    stt,
    context_agg.user(),
    llm,
    tts,
    neurosync_processor,  # Processeur corrigé
    context_agg.assistant(),
    transport.output()
])

task = PipelineTask(
    pipeline,
    params=PipelineParams(
        allow_interruptions=True,
        enable_metrics=True,
        enable_usage_metrics=True
    )
)

# Handlers Daily
@transport.event_handler("on_client_connected")
async def on_client_connected(transport, client):
    logger.info("Client connecté: %s", client.get("id"))
    
    greeting = "Ahoy moussaillon! Je suis Gala, capitaine de ce navire!"
    
    assistant_ctx = context_agg.assistant()
    assistant_ctx.add_messages([{"role": "assistant", "content": greeting}])
    
    await task.queue_frames([TTSSpeakFrame(greeting)])

@transport.event_handler("on_client_disconnected")
async def on_client_disconnected(transport, client):
    logger.info("Client déconnecté: %s", client.get("id"))
    await task.cancel()

# Main
async def main():
    logger.info("Gala • Démarrage du pipeline – salle %s", DAILY_ROOM_URL)
    
    # Vérifier l'API
    try:
        response = requests.get("http://127.0.0.1:6969/health")
        if response.status_code == 200:
            logger.info("✅ API NeuroSync accessible")
        else:
            logger.warning("⚠️ API non accessible")
    except:
        logger.warning("⚠️ Impossible de vérifier l'API")
    
    runner = PipelineRunner()
    await runner.run(task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Arrêt par l'utilisateur")
        if api_client:
            api_client.close()