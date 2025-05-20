#!/usr/bin/env python3
"""
Test simple du PCM direct
"""

import requests
import numpy as np
import time

API_URL = "http://localhost:6969"
SAMPLE_RATE = 16000

# Générer un audio de test
duration = 0.5
samples = int(SAMPLE_RATE * duration)
t = np.linspace(0, duration, samples)

# Onde sinusoïdale avec harmoniques
audio = 0.5 * np.sin(2 * np.pi * 150 * t)  # Fréquence voix
audio += 0.3 * np.sin(2 * np.pi * 300 * t)  # Harmonique

# Convertir en PCM 16-bit
audio_int16 = (audio * 16000).astype(np.int16)
pcm_data = audio_int16.tobytes()

print(f"Audio généré: {len(pcm_data)} bytes")

# Tester l'endpoint direct
print("\nTest endpoint direct...")
response = requests.post(
    f"{API_URL}/test_direct_pcm",
    data=pcm_data,
    headers={'Content-Type': 'audio/pcm'}
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    print(f"Résultat: {response.json()}")
else:
    print(f"Erreur: {response.text}")

# Tester via le buffer
print("\nTest via buffer...")
response = requests.post(
    f"{API_URL}/audio_to_blendshapes",
    data=pcm_data,
    headers={'Content-Type': 'audio/pcm'}
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    print(f"Résultat: {response.json()}")

print("\nTest terminé.")