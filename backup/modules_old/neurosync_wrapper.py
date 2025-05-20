"""
Wrapper pour utiliser le vrai modèle NeuroSync
"""
import sys
import os

# Ajouter le chemin du projet NeuroSync original au sys.path
neurosync_path = "/home/gieidi-prime/Agents/NeuroSync_Local_API/neurosync_v3_all copy/NeuroSync_Real-Time_API"
sys.path.insert(0, neurosync_path)

import torch
import numpy as np
from typing import Dict
import librosa

# Importer le modèle NeuroSync original
from models.neurosync.model.model import load_model
from models.neurosync.generate_face_shapes import generate_facial_data_from_bytes
from models.neurosync.config import config as neurosync_config

class NeuroSyncWrapper:
    """
    Wrapper pour intégrer le modèle NeuroSync existant
    """
    
    def __init__(self, config: Dict = None):
        if config is None:
            config = {}
            
        device_str = config.get("device", "cuda" if torch.cuda.is_available() else "cpu")
        self.device = torch.device(device_str)
        self.sample_rate = config.get("sample_rate", 88200)
        
        # Charger le modèle avec la configuration originale
        checkpoint_path = config.get("checkpoint_path", "models/neurosync/model/model.pth")
        
        # Utiliser le chemin du projet original si disponible
        if os.path.exists(os.path.join(neurosync_path, checkpoint_path)):
            model_path = os.path.join(neurosync_path, checkpoint_path)
        else:
            model_path = checkpoint_path
            
        self.model = load_model(model_path, device=self.device)
        
        print(f"Modèle NeuroSync chargé sur {self.device}")
        
    def process_audio(self, audio_tensor: torch.Tensor) -> torch.Tensor:
        """
        Traite l'audio et retourne les blendshapes
        
        Args:
            audio_tensor: Tensor audio [B, T] à 88200Hz
            
        Returns:
            blendshapes: Tensor [B, 68] valeurs entre 0 et 1
        """
        # L'API originale attend des bytes, donc on convertit
        audio_np = audio_tensor.cpu().numpy()[0]
        
        # Convertir en int16 pour l'API
        audio_int16 = (audio_np * 32767).astype(np.int16)
        audio_bytes = audio_int16.tobytes()
        
        # Utiliser la fonction du projet original
        result = generate_facial_data_from_bytes(
            audio_bytes, 
            sample_rate=self.sample_rate,
            device=self.device
        )
        
        # Extraire les blendshapes du résultat
        blendshapes = result['blendshapes']
        
        # Convertir en tensor
        return torch.FloatTensor(blendshapes).unsqueeze(0).to(self.device)
        
    def process_audio_bytes(self, audio_bytes: bytes, sample_rate: int = 48000) -> np.ndarray:
        """
        Traite des bytes audio et retourne les blendshapes
        
        Args:
            audio_bytes: Audio en bytes (int16)
            sample_rate: Sample rate de l'audio
            
        Returns:
            blendshapes: Array numpy [68] valeurs entre 0 et 1
        """
        # Si nécessaire, rééchantillonner
        if sample_rate != self.sample_rate:
            # Convertir en float32 pour le resampling
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_float = audio_np.astype(np.float32) / 32768.0
            
            # Rééchantillonner
            audio_resampled = librosa.resample(
                audio_float,
                orig_sr=sample_rate,
                target_sr=self.sample_rate
            )
            
            # Reconvertir en bytes
            audio_int16 = (audio_resampled * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()
            
        # Utiliser la fonction du projet original
        result = generate_facial_data_from_bytes(
            audio_bytes, 
            sample_rate=self.sample_rate,
            device=self.device
        )
        
        return result['blendshapes']
        
    def warmup(self):
        """Préchauffe le modèle pour optimiser les performances"""
        dummy_audio = np.random.randn(self.sample_rate * 2).astype(np.float32)
        dummy_bytes = (dummy_audio * 32767).astype(np.int16).tobytes()
        _ = self.process_audio_bytes(dummy_bytes, self.sample_rate)
        print("Modèle préchauffé")
        
    def get_config(self) -> Dict:
        """Retourne la configuration du modèle"""
        return {
            "sample_rate": self.sample_rate,
            "device": str(self.device),
            "model_type": "neurosync_original"
        }