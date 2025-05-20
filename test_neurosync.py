"""
Script de test pour vérifier l'intégration du modèle NeuroSync
"""

import numpy as np
import sys

try:
    from neurosync_model import neurosync_model
    print("✅ Import du modèle NeuroSync réussi")
    
    # Créer des données audio de test (silence de 1 seconde)
    sample_rate = 88200  # Selon la config
    duration = 1.0
    audio_data = np.zeros(int(sample_rate * duration), dtype=np.float32)
    audio_bytes = audio_data.tobytes()
    
    print("🧪 Test de génération de blendshapes...")
    result = neurosync_model.generate_blendshapes(audio_bytes)
    
    print(f"✅ Résultat obtenu: {type(result)}")
    if isinstance(result, dict) and 'blendshapes' in result:
        print(f"   - Nombre de frames: {len(result['blendshapes'])}")
        if result['blendshapes']:
            print(f"   - Nombre de blendshapes par frame: {len(result['blendshapes'][0])}")
    
except Exception as e:
    print(f"❌ Erreur lors du test: {str(e)}")
    import traceback
    traceback.print_exc()