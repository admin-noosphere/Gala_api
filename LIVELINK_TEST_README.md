# Test de connexion LiveLink

Ce dossier contient plusieurs scripts pour tester la connexion LiveLink entre Gala et Unreal Engine.

## Scripts disponibles

### 1. `test_livelink_connection.py`
Test basique de connexion UDP directe vers Unreal Engine.
- Envoie des paquets UDP simples avec animation idle
- N'utilise pas les modules Gala, connexion directe
- Utile pour vérifier que Unreal écoute sur le bon port

```bash
python test_livelink_connection.py
```

### 2. `test_gala_livelink.py`
Test complet utilisant les modules Gala.
- Teste la connexion WebSocket
- Teste la connexion UDP
- Teste le pipeline complet (audio → blendshapes → LiveLink)

```bash
python test_gala_livelink.py
```

### 3. `send_idle_animation.py`
Envoie une animation idle continue à Unreal Engine.
- Animation naturaliste avec respiration, clignements, micro-mouvements
- Similaire à la `default_animation` de NeuroSync_Player
- Utilise les modules Gala

```bash
python send_idle_animation.py
```

## Configuration

Avant d'exécuter les tests, vérifiez la configuration dans `config.py`:

```python
CONFIG = {
    "livelink_ip": "192.168.1.32",  # IP d'Unreal Engine
    "livelink_port": 11111,         # Port LiveLink
    "target_fps": 60,
    # ...
}
```

## Prérequis Unreal Engine

1. Ouvrir Unreal Engine
2. Activer le plugin LiveLink
3. Ajouter une source LiveLink :
   - Window → Live Link
   - Add Source → Message Bus Source
   - Ou UDP Source sur le port 11111

## Animation Idle

L'animation idle envoyée contient :
- **Respiration** : Mouvement subtil de la mâchoire et des narines
- **Clignements** : Clignements naturels toutes les 3-5 secondes
- **Micro-mouvements** : Saccades oculaires, micro-expressions
- **Tête** : Légers mouvements de rotation/inclinaison

Ces animations sont similaires à celles utilisées par NeuroSync_Player pour maintenir un personnage "vivant" quand il n'y a pas d'audio.

## Debugging

Si la connexion ne fonctionne pas :

1. Vérifier l'IP et le port dans `config.py`
2. S'assurer qu'Unreal Engine est en écoute
3. Désactiver temporairement le pare-feu
4. Utiliser Wireshark pour vérifier les paquets UDP

## Format des paquets LiveLink

Les paquets UDP suivent ce format :
```
Header: "LIVE" (4 bytes)
Subject name length (4 bytes)
Subject name (variable)
Timestamp (8 bytes, double)
Blendshapes count (4 bytes)
Blendshapes values (4 bytes each, float)
```

Les 68 blendshapes ARKit sont envoyées dans l'ordre standard.