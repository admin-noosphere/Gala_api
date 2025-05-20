# Approche NeuroSync_Player pour Gala v1

Ce projet utilise maintenant la même approche que NeuroSync_Player pour la connexion LiveLink, offrant une meilleure compatibilité avec Unreal Engine.

## Composants principaux

### 1. PyLiveLinkFace (`modules/pylivelinkface.py`)
- Implémente le protocole LiveLink binaire
- Compatible avec Unreal Engine 5
- Gère 61 blendshapes au format natif LiveLink
- Basé sur l'implémentation de NeuroSync_Player

### 2. LiveLinkNeuroSync (`modules/livelink_neurosync.py`)
- Client LiveLink utilisant PyLiveLinkFace
- Connexion UDP vers Unreal Engine
- Conversion automatique ARKit (68) → LiveLink (61)
- Support des animations idle

### 3. API Client (`api_client_neurosync.py`)
- API REST recevant l'audio de Pipecat
- Conversion audio → blendshapes via NeuroSync
- Envoi direct à Unreal via LiveLink

## Architecture

```
[Pipecat Audio] → [API Gala] → [NeuroSync Model] → [PyLiveLinkFace] → [Unreal Engine]
192.168.1.32:6969                                                     192.168.1.14:11111
```

## Utilisation

### 1. Lancer l'API
```bash
python api_client_neurosync.py
```
Ou après migration :
```bash
python api_client.py
```

### 2. Tester la connexion
```bash
python test_neurosync_livelink.py
```

### 3. Animation idle
```bash
python idle_animation_neurosync.py
```

## Format des données

### Blendshapes ARKit (68 valeurs)
Les 68 blendshapes standard d'Apple ARKit incluent :
- 52 expressions faciales de base
- Mouvements de tête (yaw, pitch, roll)
- Duplicatas pour compatibilité
- Émotions supplémentaires

### Blendshapes LiveLink (61 valeurs)
Le format natif d'Unreal Engine avec :
- 52 expressions faciales ARKit
- 9 valeurs custom (non utilisées)
- Pas de mouvements de tête (gérés séparément)

### Conversion automatique
Le système convertit automatiquement :
- ARKit index 0-51 → LiveLink index 0-51 (direct)
- ARKit index 54-55 (duplicatas) → LiveLink 0,7
- Autres indices ignorés ou mappés

## Animation Idle

L'animation idle (similaire à NeuroSync_Player) inclut :

1. **Respiration** (cycle de 2 secondes)
   - JawOpen subtil
   - Mouvements des narines
   - Expansion légère des joues

2. **Clignements naturels**
   - Toutes les 3-5 secondes
   - Durée variable
   - Synchronisés gauche/droite

3. **Micro-mouvements**
   - Saccades oculaires
   - Mouvements de sourcils
   - Micro-sourires occasionnels

4. **Variabilité**
   - Timing non régulier
   - Amplitudes variables
   - Patterns naturels

## Migration

Pour passer à la nouvelle approche :

```bash
python migrate_to_neurosync.py
```

Cela :
1. Sauvegarde les anciens fichiers
2. Met à jour l'API client
3. Active PyLiveLinkFace

## Debugging

### Vérifier la connexion
```bash
# Diagnostic réseau
python diagnose_livelink.py

# Test simple
python test_neurosync_livelink.py
```

### Format des paquets UDP
Les paquets LiveLink suivent le format binaire :
- Header version (4 bytes)
- UUID (36 bytes)
- Subject name
- Timestamp
- Frame rate
- 61 float values

### Logs utiles
- Frames envoyées
- Valeurs des blendshapes
- Erreurs de connexion

## Avantages de cette approche

1. **Compatibilité maximale** avec Unreal Engine
2. **Protocole natif** LiveLink
3. **Performance optimale** (binaire vs JSON)
4. **Animation fluide** à 60 FPS
5. **Idle naturel** intégré

## Configuration Unreal Engine

1. Activer le plugin LiveLink
2. Ajouter une source Message Bus ou UDP
3. Port : 11111
4. Subject : "GalaFace"
5. Mapper aux blendshapes du personnage

L'approche NeuroSync_Player garantit une meilleure intégration avec Unreal Engine et des animations plus naturelles.