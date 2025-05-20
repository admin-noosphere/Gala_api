# Gala v1 - Guide de Démarrage Rapide

## Installation

1. **Configurer et copier le modèle NeuroSync** :
```bash
cd /home/gieidi-prime/Agents/Claude/Gala_v1
./setup.sh
```

## Chemin du Modèle

Le modèle NeuroSync doit être placé dans :
```
/home/gieidi-prime/Agents/Claude/Gala_v1/models/neurosync/model/model.pth
```

Le script `setup.sh` copie automatiquement le modèle depuis :
```
/home/gieidi-prime/Agents/NeuroSync_Local_API/neurosync_v3_all copy/NeuroSync_Real-Time_API/models/neurosync
```

## Lancement de l'API

```bash
cd /home/gieidi-prime/Agents/Claude/Gala_v1
python api_client.py
```

L'API démarrera sur le port 6969.

## Test Rapide

```python
import requests
import numpy as np

# Générer un son de test (440 Hz, 1 seconde)
duration = 1.0
sample_rate = 48000
t = np.linspace(0, duration, int(sample_rate * duration))
audio = np.sin(2 * np.pi * 440 * t)
audio_int16 = (audio * 32767).astype(np.int16)

# Envoyer à l'API
response = requests.post(
    'http://localhost:6969/audio_to_blendshapes',
    data=audio_int16.tobytes(),
    headers={'Content-Type': 'audio/wav'}
)

print(response.json())
```

## Structure des Fichiers

```
Gala_v1/
├── api_client.py          # API principale
├── config.py              # Configuration
├── modules/               # Modules de l'API
│   ├── neurosync_model.py
│   ├── audio_processor.py
│   └── livelink_client.py
├── models/                # Modèle NeuroSync
│   └── neurosync/
│       └── model/
│           └── model.pth
└── requirements.txt
```

## Fonctionnement

1. **Input** : Audio 48kHz, mono, 16-bit PCM
2. **Processing** : Modèle NeuroSync (réchantillonné à 88.2kHz en interne)
3. **Output** : 68 blendshapes ARKit
4. **Transmission** : LiveLink vers Unreal Engine (port 11111)

## Endpoints

- `POST /audio_to_blendshapes` - Conversion directe audio → blendshapes
- `POST /stream_audio` - Streaming avec buffer d'accumulation

## Confirmation

✅ Le modèle est au bon emplacement
✅ La configuration pointe vers le bon fichier
✅ L'API fonctionne comme l'originale
✅ Compatible avec le Player existant