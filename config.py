"""
Configuration centrale pour Gala v1
"""

import os
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class AudioConfig:
    """Configuration audio"""
    sample_rate: int = 48000
    channels: int = 1
    bit_depth: int = 16
    format: str = "int16"
    min_buffer_ms: int = 200
    max_buffer_ms: int = 1000
    
@dataclass
class ModelConfig:
    """Configuration du modèle NeuroSync"""
    model_path: str = "models/neurosync/model/model.pth"
    model_sample_rate: int = 88200
    sequence_length: int = 1024
    use_cuda: bool = True
    use_fp16: bool = True
    batch_size: int = 1
    
@dataclass
class LiveLinkConfig:
    """Configuration LiveLink"""
    host: str = "127.0.0.1"
    port: int = 11111
    subject_name: str = "GalaFace"
    fps: int = 60
    use_compression: bool = True
    
@dataclass
class APIConfig:
    """Configuration de l'API"""
    host: str = "0.0.0.0"
    port: int = 6969
    debug: bool = False
    cors_origins: List[str] = None
    
    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"]
            
@dataclass
class GalaConfig:
    """Configuration complète de Gala v1"""
    audio: AudioConfig = AudioConfig()
    model: ModelConfig = ModelConfig()
    livelink: LiveLinkConfig = LiveLinkConfig()
    api: APIConfig = APIConfig()
    
    # Paths
    base_dir: str = os.path.dirname(os.path.abspath(__file__))
    models_dir: str = os.path.join(base_dir, "models")
    cache_dir: str = os.path.join(base_dir, ".cache")
    
    # Features
    enable_tts: bool = False
    enable_stt: bool = False
    enable_llm: bool = False
    
    # Performance
    num_workers: int = 4
    pin_memory: bool = True
    prefetch_factor: int = 2
    
    def __post_init__(self):
        # Créer les dossiers nécessaires
        os.makedirs(self.models_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)
        
    @classmethod
    def from_env(cls) -> 'GalaConfig':
        """Charge la config depuis les variables d'environnement"""
        config = cls()
        
        # Override avec les variables d'env si présentes
        if os.getenv("GALA_SAMPLE_RATE"):
            config.audio.sample_rate = int(os.getenv("GALA_SAMPLE_RATE"))
        if os.getenv("GALA_API_PORT"):
            config.api.port = int(os.getenv("GALA_API_PORT"))
        if os.getenv("GALA_LIVELINK_PORT"):
            config.livelink.port = int(os.getenv("GALA_LIVELINK_PORT"))
        if os.getenv("GALA_DEBUG"):
            config.api.debug = os.getenv("GALA_DEBUG").lower() == "true"
            
        return config

# Instance globale
config = GalaConfig.from_env()

# Dictionnaire CONFIG pour compatibilité avec les anciens scripts
CONFIG = {
    "sample_rate": config.audio.sample_rate,
    "audio_format": config.audio.format,
    "channels": config.audio.channels,
    "min_audio_ms": config.audio.min_buffer_ms,
    "target_fps": config.livelink.fps,
    "blendshapes_count": 68,
    "model_path": config.model.model_path,
    "livelink_ip": "192.168.1.14",  # IP d'Unreal Engine LiveLink
    "livelink_port": config.livelink.port,
    "api_port": config.api.port,
    "api_host": "192.168.1.32"  # IP du serveur API Gala
}
