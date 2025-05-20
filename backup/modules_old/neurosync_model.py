"""
Module de modèle NeuroSync pour l'API Gala.
Utilise le vrai modèle NeuroSync du projet NeuroSync_Local_API
"""

import sys
import os
import torch

# Ajouter le chemin vers le projet NeuroSync original
NEUROSYNC_PATH = "/home/gieidi-prime/Agents/NeuroSync_Local_API/neurosync_v3_all copy/NeuroSync_Real-Time_API"
sys.path.insert(0, NEUROSYNC_PATH)

# Importer les modules nécessaires du projet NeuroSync
from models.neurosync.config import config
from models.neurosync.model.model import load_model
from utils.utils_audio import process_blendshapes

class NeuroSyncModel:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🔧 Initialisation du modèle NeuroSync sur {self.device}")
        
        # Charger le modèle réel
        model_path = os.path.join(NEUROSYNC_PATH, 'models/neurosync/model/model.pth')
        self.model = load_model(model_path, config, self.device)
        self.config = config
        print("✅ Modèle NeuroSync chargé avec succès")
    
    def generate_blendshapes(self, audio_data):
        """
        Génère des blendshapes à partir de données audio.
        
        Args:
            audio_data: Données audio sous forme de bytes
            
        Returns:
            dict: Résultat contenant les blendshapes
        """
        try:
            # Utiliser la fonction du projet original pour traiter les blendshapes
            result = process_blendshapes(audio_data, self.model, self.device, self.config)
            return result
        except Exception as e:
            print(f"❌ Erreur lors de la génération des blendshapes: {str(e)}")
            raise

# Instance unique du modèle
neurosync_model = NeuroSyncModel()