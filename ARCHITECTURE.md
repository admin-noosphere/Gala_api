# Architecture Gala v1

## Vue d'ensemble

```
[Pipecat/Client Audio] → [API Gala] → [LiveLink] → [Unreal Engine]
   192.168.1.32:6969                               192.168.1.14:11111
```

## Composants

### 1. API Gala (192.168.1.32:6969)
- Héberge l'API REST qui reçoit l'audio
- Utilise le modèle NeuroSync pour convertir audio → blendshapes
- Envoie les blendshapes à Unreal via LiveLink

### 2. Unreal Engine LiveLink (192.168.1.14:11111)
- Reçoit les blendshapes via UDP/WebSocket
- Applique les animations au personnage 3D
- Doit avoir le plugin LiveLink activé

### 3. Client Pipecat
- Envoie l'audio à l'API Gala
- Peut être sur n'importe quelle machine du réseau

## Flux de données

1. **Audio Input** → Pipecat capture l'audio
2. **HTTP POST** → Audio envoyé à `http://192.168.1.32:6969/audio_to_blendshapes`
3. **NeuroSync** → Conversion audio → 68 blendshapes ARKit
4. **LiveLink** → Blendshapes envoyées à `192.168.1.14:11111` (UDP)
5. **Unreal** → Animation appliquée au personnage

## Configuration

### Sur la machine API (192.168.1.32)
```python
CONFIG = {
    "api_port": 6969,
    "livelink_ip": "192.168.1.14",
    "livelink_port": 11111
}
```

### Dans Unreal Engine (192.168.1.14)
1. Activer le plugin LiveLink
2. Ajouter une source LiveLink UDP sur le port 11111
3. Mapper le sujet "GalaFace" au personnage

## Test de connexion

### 1. Tester l'API
```bash
curl http://192.168.1.32:6969/health
```

### 2. Tester LiveLink
```bash
python test_livelink_connection.py
```

### 3. Envoyer une animation idle
```bash
python send_idle_animation.py
```

## Debugging

Si la connexion ne fonctionne pas :

1. Vérifier que l'API est accessible :
   ```bash
   ping 192.168.1.32
   curl http://192.168.1.32:6969/health
   ```

2. Vérifier qu'Unreal est accessible :
   ```bash
   ping 192.168.1.14
   ```

3. Utiliser le script de diagnostic :
   ```bash
   python diagnose_livelink.py
   ```

4. Vérifier les pare-feu sur les deux machines

## Animation Idle

L'animation idle (similaire à NeuroSync_Player) contient :
- Respiration subtile (JawOpen, CheekPuff)
- Clignements naturels toutes les 3-5 secondes
- Micro-mouvements des yeux (saccades)
- Expressions faciales légères
- Mouvements de tête minimes

Cette animation maintient le personnage "vivant" quand il n'y a pas d'audio.