# Gala v1 - API Unifiée Audio-Visuelle

## Description
Gala v1 est une application conversationnelle qui utilise une API unifiée pour créer un avatar pirate digital interactif. Le système intègre :
- **STT** (Speech-to-Text) : Conversion audio → texte
- **LLM** (Large Language Model) : Génération de réponses contextuelles 
- **TTS** (Text-to-Speech) : Conversion texte → audio
- **NeuroSync** : Conversion audio → blendshapes ARKit
- **LiveLink** : Transmission des blendshapes vers Unreal Engine

## Architecture

```
Flux de données:
┌─────────┐    ┌─────┐    ┌─────┐    ┌─────┐    ┌──────────────┐    ┌──────────┐
│ Audio   │ -> │ STT │ -> │ LLM │ -> │ TTS │ -> │ API Unifiée  │ -> │ LiveLink │
│ Entrée  │    │     │    │     │    │     │    │ (Blendshapes)│    │   (UE)   │
└─────────┘    └─────┘    └─────┘    └─────┘    └──────────────┘    └──────────┘
```

## Structure du projet
```
Gala_v1/
├── main.py               # Application principale (nouveau)
├── api_client.py         # API unifiée REST
├── config.py            # Configuration centralisée
├── modules/             # Modules réutilisables
│   ├── neurosync_simple.py
│   ├── audio_processor.py
│   └── livelink_client.py
├── models/              # Modèles NeuroSync
├── requirements.txt     # Dépendances
├── .env.example        # Exemple de configuration
├── start_gala.sh       # Script de démarrage
└── README.md           # Documentation
```

## Installation

1. **Cloner le projet** :
```bash
cd /home/gieidi-prime/Agents/Claude/Gala_v1
```

2. **Installer les dépendances** :
```bash
pip install -r requirements.txt
```

3. **Configurer les variables d'environnement** :
```bash
cp .env.example .env
nano .env  # Ajouter vos clés API
```

4. **Vérifier le modèle NeuroSync** :
```bash
ls -la models/neurosync/model/model.pth
```

## Configuration

### Variables d'environnement requises :
- `OPENAI_API_KEY` : Pour STT (Whisper) et LLM (GPT-4)
- `ELEVENLABS_API_KEY` : (Optionnel) Pour une voix plus réaliste

### Ports par défaut :
- API unifiée : `6969`
- LiveLink : `11111`

## Utilisation

### Méthode 1 : Script automatique
```bash
chmod +x start_gala.sh
./start_gala.sh
```

### Méthode 2 : Lancement manuel

1. **Démarrer l'API unifiée** :
```bash
python api_client.py
```

2. **Dans un autre terminal, lancer Gala** :
```bash
python main.py
```

## Endpoints API

### POST /audio_to_blendshapes
Convertit de l'audio en blendshapes ARKit.

**Requête** :
```bash
curl -X POST http://localhost:6969/audio_to_blendshapes \
  -H "Content-Type: audio/wav" \
  --data-binary @audio.wav
```

**Réponse** :
```json
{
  "blendshapes": [0.1, 0.2, ...],  // 68 valeurs
  "blendshape_names": ["EyeBlinkLeft", ...],
  "timestamp": 1234567890.123,
  "fps": 60
}
```

### POST /stream_audio
Version streaming avec buffering automatique.

## Test

1. **Test de l'API** :
```bash
python test_gala.py
```

2. **Test complet avec audio** :
```bash
python test_neurosync.py
```

## Intégration Unreal Engine

1. Assurez-vous que LiveLink est activé dans Unreal
2. Configurez le sujet LiveLink : `GalaFace`
3. L'API envoie automatiquement les blendshapes sur le port `11111`

## Architecture détaillée

### main.py
- Gère le flux conversationnel complet
- Coordonne STT → LLM → TTS → API
- Personnalité de Gala le pirate

### api_client.py
- Serveur Flask REST
- Gère la conversion audio → blendshapes
- Transmet à LiveLink via websocket

### modules/
- `neurosync_simple.py` : Wrapper simplifié du modèle
- `audio_processor.py` : Traitement audio (resampling, buffering)
- `livelink_client.py` : Client LiveLink pour Unreal

## Dépannage

### L'API ne démarre pas
```bash
# Vérifier le port
lsof -i :6969
# Tuer le processus si nécessaire
kill -9 $(lsof -t -i:6969)
```

### Pas de connexion LiveLink
```bash
# Vérifier la connexion
telnet localhost 11111
```

### Erreur de modèle
```bash
# Vérifier le modèle
ls -la models/neurosync/model/model.pth
```

## Personnalisation

### Changer la personnalité de Gala
Modifier dans `main.py` :
```python
personality: str = """
    Tu es Gala, un pirate digital...
"""
```

### Ajuster les paramètres audio
Modifier dans `config.py` :
```python
sample_rate: int = 48000
min_buffer_ms: int = 200
```

## Performance

- FPS cible : 60
- Latence : ~200ms (audio → blendshapes)
- Buffer audio : 200-1000ms

## Développement

### Ajouter un nouveau service STT/TTS
1. Créer une classe dans `modules/`
2. Implémenter l'interface dans `main.py`
3. Ajouter la configuration dans `config.py`

### Modifier le modèle NeuroSync
1. Placer le nouveau modèle dans `models/neurosync/model/`
2. Mettre à jour `modules/neurosync_simple.py`

## Licence
[À définir]

## Support
Pour toute question, consultez les logs :
```bash
tail -f api.log
```