"""
Utilisation directe du modèle NeuroSync
"""
import sys
import os

# Ajouter le chemin du projet NeuroSync original
neurosync_path = "/home/gieidi-prime/Agents/NeuroSync_Local_API/neurosync_v3_all copy/NeuroSync_Real-Time_API"
sys.path.insert(0, neurosync_path)

import torch
import numpy as np
from typing import Dict, Tuple
import librosa

# Importer les modules NeuroSync
from models.neurosync.model.model import create_model, load_model
from models.neurosync.generate_face_shapes import generate_facial_data_from_bytes
from models.neurosync.config import create_hparams

class NeuroSyncDirect:
    """
    Wrapper direct pour utiliser le modèle NeuroSync
    """
    
    def __init__(self, device: str = "cuda"):
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        
        # Créer la configuration
        config_path = os.path.join(neurosync_path, "models/neurosync/config.json")
        self.config = create_hparams(config_path)
        
        # Charger le modèle
        model_path = os.path.join(neurosync_path, "models/neurosync/model/model.pth")
        self.model = load_model(
            self.config,
            checkpoint_path=model_path,
            device=self.device
        )
        
        self.sample_rate = 88200
        print(f"Modèle NeuroSync chargé sur {self.device}")
        
    def process_audio_bytes(self, audio_bytes: bytes, sample_rate: int = 48000) -> np.ndarray:
        """
        Traite des bytes audio et retourne les blendshapes
        """
        # Rééchantillonner si nécessaire
        if sample_rate != self.sample_rate:
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_float = audio_np.astype(np.float32) / 32768.0
            
            audio_resampled = librosa.resample(
                audio_float,
                orig_sr=sample_rate,
                target_sr=self.sample_rate
            )
            
            audio_int16 = (audio_resampled * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()
            
        # Appeler la fonction avec tous les paramètres
        result = generate_facial_data_from_bytes(
            audio_bytes,
            model=self.model,
            device=self.device,
            config=self.config
        )
        
        # Les résultats sont déjà un array numpy de 68 valeurs
        return result
        
    def process_audio(self, audio_tensor: torch.Tensor) -> torch.Tensor:
        """
        Traite un tensor audio et retourne les blendshapes
        """
        # Convertir en bytes
        audio_np = audio_tensor.cpu().numpy()[0]
        audio_int16 = (audio_np * 32767).astype(np.int16)
        audio_bytes = audio_int16.tobytes()
        
        # Traiter
        blendshapes = self.process_audio_bytes(audio_bytes, self.sample_rate)
        
        # Retourner comme tensor
        return torch.FloatTensor(blendshapes).unsqueeze(0).to(self.device)
        
    def warmup(self):
        """Préchauffe le modèle"""
        dummy_audio = np.random.randn(self.sample_rate * 2).astype(np.float32)
        dummy_bytes = (dummy_audio * 32767).astype(np.int16).tobytes()
        _ = self.process_audio_bytes(dummy_bytes, self.sample_rate)
        print("Modèle préchauffé")