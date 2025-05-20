#!/usr/bin/env python3
"""
Script de diagnostic pour la connexion LiveLink
Vérifie la configuration réseau et teste différents modes de connexion
"""

import socket
import subprocess
import platform
import time
import struct
import json
from typing import Dict, List, Tuple

def check_network_connectivity() -> Dict[str, any]:
    """Vérifie la connectivité réseau de base"""
    results = {
        "hostname": socket.gethostname(),
        "local_ips": [],
        "can_resolve_dns": False,
        "platform": platform.system()
    }
    
    # Obtenir toutes les IPs locales
    try:
        hostname = socket.gethostname()
        ips = socket.gethostbyname_ex(hostname)[2]
        results["local_ips"] = [ip for ip in ips if not ip.startswith("127.")]
        
        # Ajouter l'IP principale
        results["primary_ip"] = socket.gethostbyname(hostname)
    except Exception as e:
        results["ip_error"] = str(e)
    
    # Test DNS
    try:
        socket.gethostbyname("google.com")
        results["can_resolve_dns"] = True
    except:
        pass
    
    return results

def test_port_availability(port: int) -> bool:
    """Vérifie si un port est disponible localement"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("0.0.0.0", port))
        sock.close()
        return True
    except:
        return False

def scan_for_livelink_servers(network_prefix: str = "192.168.1", 
                              port: int = 11111, 
                              timeout: float = 0.1) -> List[str]:
    """Scanne le réseau local pour trouver des serveurs LiveLink"""
    active_hosts = []
    
    print(f"Scan du réseau {network_prefix}.0/24 sur le port {port}...")
    
    for i in range(1, 255):
        host = f"{network_prefix}.{i}"
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        
        try:
            # Envoyer un paquet de test
            test_packet = b'LIVE' + struct.pack('I', 4) + b'TEST'
            sock.sendto(test_packet, (host, port))
            
            # Attendre une réponse (même si on n'en attend pas vraiment)
            sock.recv(1024)
            active_hosts.append(host)
        except socket.timeout:
            pass
        except Exception:
            pass
        finally:
            sock.close()
    
    return active_hosts

def test_udp_connectivity(host: str, port: int) -> Tuple[bool, str]:
    """Test la connectivité UDP vers un hôte spécifique"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        # Créer un paquet LiveLink valide
        packet = b'LIVE'
        subject_name = b'TestConnection'
        packet += struct.pack('I', len(subject_name))
        packet += subject_name
        packet += struct.pack('d', time.time())
        packet += struct.pack('I', 68)  # 68 blendshapes
        packet += b'\x00' * (68 * 4)  # Valeurs à zéro
        
        # Envoyer le paquet
        sock.sendto(packet, (host, port))
        
        # Attendre brièvement une réponse (généralement pas de réponse attendue)
        sock.settimeout(0.5)
        try:
            data, addr = sock.recvfrom(1024)
            return True, f"Réponse reçue de {addr}"
        except socket.timeout:
            return True, "Paquet envoyé (pas de réponse attendue)"
            
    except Exception as e:
        return False, str(e)
    finally:
        sock.close()

def diagnose_firewall() -> Dict[str, any]:
    """Diagnostic du pare-feu"""
    results = {
        "platform": platform.system(),
        "firewall_commands": []
    }
    
    if platform.system() == "Linux":
        results["firewall_commands"] = [
            "sudo ufw status",
            "sudo iptables -L -n",
            f"sudo ufw allow 11111/udp"  # Pour autoriser le port
        ]
    elif platform.system() == "Windows":
        results["firewall_commands"] = [
            "netsh advfirewall show allprofiles",
            "netsh advfirewall firewall show rule name=all",
            f'netsh advfirewall firewall add rule name="LiveLink" dir=out action=allow protocol=UDP localport=11111'
        ]
    elif platform.system() == "Darwin":  # macOS
        results["firewall_commands"] = [
            "sudo pfctl -s info",
            "/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate"
        ]
    
    return results

def main():
    """Diagnostic principal"""
    print("=== Diagnostic LiveLink ===\n")
    
    # 1. Vérifier la connectivité réseau
    print("1. Vérification de la connectivité réseau...")
    network_info = check_network_connectivity()
    print(f"   Hostname: {network_info['hostname']}")
    print(f"   IPs locales: {network_info['local_ips']}")
    print(f"   IP principale: {network_info.get('primary_ip', 'Non trouvée')}")
    print(f"   DNS fonctionnel: {'Oui' if network_info['can_resolve_dns'] else 'Non'}")
    print()
    
    # 2. Vérifier les ports
    print("2. Vérification des ports...")
    test_ports = [11111, 11112, 11113]  # Ports LiveLink courants
    for port in test_ports:
        available = test_port_availability(port)
        print(f"   Port {port}: {'Disponible' if available else 'Occupé'}")
    print()
    
    # 3. Scanner le réseau local
    print("3. Scan du réseau local...")
    network_prefix = '.'.join(network_info.get('primary_ip', '192.168.1.1').split('.')[:-1])
    active_hosts = scan_for_livelink_servers(network_prefix)
    if active_hosts:
        print(f"   Serveurs potentiels trouvés: {active_hosts}")
    else:
        print("   Aucun serveur LiveLink détecté")
    print()
    
    # 4. Test de connexion spécifique
    print("4. Test de connexion vers Unreal Engine...")
    test_hosts = ["192.168.1.14"]  # IP d'Unreal Engine LiveLink
    if network_info.get('primary_ip'):
        test_hosts.append(network_info['primary_ip'])
    
    for host in test_hosts:
        print(f"   Test vers {host}:11111...")
        success, message = test_udp_connectivity(host, 11111)
        print(f"   {'✓' if success else '✗'} {message}")
    print()
    
    # 5. Diagnostic du pare-feu
    print("5. Diagnostic du pare-feu...")
    firewall_info = diagnose_firewall()
    print(f"   Plateforme: {firewall_info['platform']}")
    print("   Commandes utiles pour vérifier/configurer le pare-feu:")
    for cmd in firewall_info['firewall_commands']:
        print(f"     {cmd}")
    print()
    
    # 6. Recommandations
    print("6. Recommandations:")
    print("   - Assurez-vous qu'Unreal Engine est lancé avec LiveLink activé")
    print("   - Vérifiez que l'IP dans config.py correspond à celle d'Unreal")
    print("   - Désactivez temporairement le pare-feu pour tester")
    print("   - Utilisez Wireshark pour capturer les paquets UDP")
    print("   - Vérifiez que le plugin LiveLink est activé dans Unreal")
    print("\n   Configuration LiveLink dans Unreal:")
    print("   1. Window → Live Link")
    print("   2. Source → Add Source → Message Bus Source")
    print("   3. Ou créez une source UDP sur le port 11111")

if __name__ == "__main__":
    main()