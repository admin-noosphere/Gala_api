#!/usr/bin/env python3
"""
Script de migration pour passer à l'approche NeuroSync_Player
"""

import shutil
import os


def backup_current_files():
    """Sauvegarde les fichiers actuels"""
    backup_dir = "backup_before_neurosync"
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = [
        "api_client.py",
        "modules/livelink_client.py"
    ]
    
    for file in files_to_backup:
        if os.path.exists(file):
            dest = os.path.join(backup_dir, file)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(file, dest)
            print(f"Sauvegardé: {file} → {dest}")


def apply_neurosync_approach():
    """Applique l'approche NeuroSync_Player"""
    print("\n=== Migration vers l'approche NeuroSync_Player ===")
    
    # 1. Sauvegarder les fichiers actuels
    print("\n1. Sauvegarde des fichiers actuels...")
    backup_current_files()
    
    # 2. Créer les liens symboliques ou copier les nouveaux fichiers
    print("\n2. Application de la nouvelle approche...")
    
    # Remplacer l'API client
    if os.path.exists("api_client_neurosync.py"):
        shutil.copy2("api_client_neurosync.py", "api_client.py")
        print("✓ API client mise à jour avec PyLiveLinkFace")
    
    # Les nouveaux modules sont déjà créés:
    # - modules/pylivelinkface.py
    # - modules/livelink_neurosync.py
    
    print("\n3. Fichiers créés:")
    print("✓ modules/pylivelinkface.py - Protocole LiveLink compatible")
    print("✓ modules/livelink_neurosync.py - Client LiveLink style NeuroSync")
    print("✓ test_neurosync_livelink.py - Tests de connexion")
    print("✓ idle_animation_neurosync.py - Animation idle")
    
    print("\n=== Migration terminée ===")
    print("\nPour tester:")
    print("1. Lancer l'API: python api_client.py")
    print("2. Tester la connexion: python test_neurosync_livelink.py")
    print("3. Animation idle: python idle_animation_neurosync.py")
    
    print("\nLes anciens fichiers sont sauvegardés dans 'backup_before_neurosync/'")


def show_differences():
    """Montre les différences principales"""
    print("\n=== Différences principales ===")
    
    print("\nAncienne approche:")
    print("- WebSocket ou UDP simple")
    print("- Format JSON pour les données")
    print("- 68 blendshapes ARKit")
    
    print("\nNouvelle approche (NeuroSync_Player):")
    print("- Protocole LiveLink binaire")
    print("- PyLiveLinkFace pour l'encodage")
    print("- 61 blendshapes LiveLink")
    print("- Compatibilité maximale avec Unreal Engine")
    print("- Animation idle intégrée")
    
    print("\n=== Configuration ===")
    print("IP Unreal Engine: 192.168.1.14")
    print("Port LiveLink: 11111")
    print("IP API Gala: 192.168.1.32")
    print("Port API: 6969")


if __name__ == "__main__":
    print("=== Migration Gala v1 vers approche NeuroSync_Player ===")
    
    # Afficher les différences
    show_differences()
    
    # Demander confirmation
    response = input("\nVoulez-vous appliquer la migration? (y/n): ")
    
    if response.lower() == 'y':
        apply_neurosync_approach()
    else:
        print("Migration annulée.")
        print("\nVous pouvez tester la nouvelle approche avec:")
        print("- python test_neurosync_livelink.py")
        print("- python api_client_neurosync.py (au lieu de api_client.py)")