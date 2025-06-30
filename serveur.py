import socket
import threading
import json
import hashlib
import os
from datetime import datetime
from colorama import init, Fore, Style

# Initialiser colorama
init(autoreset=True)

clients = {}  # socket: pseudo
pseudos = set()
users_file = "users.json"

# Charger ou créer le fichier d'utilisateurs
if not os.path.exists(users_file):
    with open(users_file, "w") as f:
        json.dump({}, f)

with open(users_file, "r") as f:
    users = json.load(f)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def save_users():
    with open(users_file, "w") as f:
        json.dump(users, f)

def format_timestamp():
    """Retourne l'horodatage formaté"""
    return datetime.now().strftime("[%H:%M]")

def log_server(message, level="INFO"):
    """Log serveur avec couleurs"""
    timestamp = format_timestamp()
    if level == "ERROR":
        print(f"{Fore.RED}{timestamp} [ERROR] {message}")
    elif level == "SUCCESS":
        print(f"{Fore.GREEN}{timestamp} [SUCCESS] {message}")
    elif level == "WARNING":
        print(f"{Fore.YELLOW}{timestamp} [WARNING] {message}")
    else:
        print(f"{Fore.CYAN}{timestamp} [INFO] {message}")

def handle_client(client_socket):
    pseudo = ""
    try:
        client_socket.send("Tapez 1 pour connexion, 2 pour inscription: ".encode())
        choice = client_socket.recv(1024).decode()

        client_socket.send("Pseudo: ".encode())
        pseudo = client_socket.recv(1024).decode()
        client_socket.send("Mot de passe: ".encode())
        password = client_socket.recv(1024).decode()

        if choice == "1":  # Connexion
            if pseudo not in users or users[pseudo] != hash_password(password) or pseudo in pseudos:
                client_socket.send("AUTH_FAIL".encode())
                client_socket.close()
                log_server(f"Échec de connexion pour {pseudo}", "WARNING")
                return
        elif choice == "2":  # Inscription
            if pseudo in users:
                client_socket.send("PSEUDO_EXIST".encode())
                client_socket.close()
                log_server(f"Tentative d'inscription avec pseudo existant: {pseudo}", "WARNING")
                return
            users[pseudo] = hash_password(password)
            save_users()
            log_server(f"Nouvel utilisateur inscrit: {pseudo}", "SUCCESS")
        else:
            client_socket.send("CHOIX_INVALIDE".encode())
            client_socket.close()
            return

        client_socket.send("AUTH_OK".encode())
        clients[client_socket] = pseudo
        pseudos.add(pseudo)
        
        # Message de bienvenue avec horodatage
        welcome_msg = f"SYSTEM:{format_timestamp()} Bienvenue {pseudo}! Tapez /help pour voir les commandes"
        client_socket.send(welcome_msg.encode())
        
        broadcast(f"SYSTEM:{format_timestamp()} {pseudo} a rejoint le chat", client_socket)
        log_server(f"{pseudo} s'est connecté", "SUCCESS")

        while True:
            msg = client_socket.recv(1024).decode()
            if not msg:
                break
                
            if msg == "/list":
                connected = ", ".join(pseudos)
                response = f"SYSTEM:{format_timestamp()} Connectés ({len(pseudos)}): {connected}"
                client_socket.send(response.encode())
                
            elif msg == "/help":
                help_text = f"""HELP:{format_timestamp()} 📋 COMMANDES DISPONIBLES:
/help - Afficher cette aide
/list - Lister les utilisateurs connectés  
/msg <user> <message> - Envoyer un message privé
/quit - Quitter le chat"""
                client_socket.send(help_text.encode())
                
            elif msg.startswith("/msg"):
                parts = msg.split(" ", 2)
                if len(parts) == 3:
                    dest_pseudo, message = parts[1], parts[2]
                    if send_private(pseudo, dest_pseudo, message):
                        # Confirmer l'envoi à l'expéditeur
                        confirm_msg = f"PRIVATE_SENT:{format_timestamp()} Message privé envoyé à {dest_pseudo}: {message}"
                        client_socket.send(confirm_msg.encode())
                        log_server(f"Message privé de {pseudo} vers {dest_pseudo}")
                    else:
                        error_msg = f"ERROR:{format_timestamp()} Utilisateur '{dest_pseudo}' introuvable"
                        client_socket.send(error_msg.encode())
                else:
                    error_msg = f"ERROR:{format_timestamp()} Usage: /msg <utilisateur> <message>"
                    client_socket.send(error_msg.encode())
                    
            elif msg == "/quit":
                break
                
            else:
                # Message public avec horodatage
                public_msg = f"PUBLIC:{format_timestamp()} [{pseudo}] {msg}"
                broadcast(public_msg, client_socket)
                log_server(f"[{pseudo}] {msg}")

    except Exception as e:
        log_server(f"Erreur avec le client {pseudo}: {e}", "ERROR")
    finally:
        pseudos.discard(clients.get(client_socket, ""))
        if pseudo:
            broadcast(f"SYSTEM:{format_timestamp()} {pseudo} a quitté le chat", client_socket)
            log_server(f"{pseudo} s'est déconnecté", "WARNING")
        clients.pop(client_socket, None)
        client_socket.close()

def broadcast(message, sender):
    """Diffuse un message à tous les clients sauf l'expéditeur"""
    disconnected = []
    for client in clients:
        if client != sender:
            try:
                client.send(message.encode())
            except:
                disconnected.append(client)
    
    # Nettoyer les clients déconnectés
    for client in disconnected:
        pseudos.discard(clients.get(client, ""))
        clients.pop(client, None)
        try:
            client.close()
        except:
            pass

def send_private(from_user, to_user, message):
    """Envoie un message privé avec notification"""
    for client, pseudo in clients.items():
        if pseudo == to_user:
            try:
                private_msg = f"PRIVATE:{format_timestamp()} [Privé de {from_user}] {message}"
                client.send(private_msg.encode())
                return True
            except:
                return False
    return False

# Démarrage du serveur avec interface améliorée
print(f"{Fore.GREEN + Style.BRIGHT}╔{'═' * 50}╗")
print(f"{Fore.GREEN + Style.BRIGHT}║{' ' * 10}SERVEUR MESSAGERIE DÉMARRÉ{' ' * 11}║")
print(f"{Fore.GREEN + Style.BRIGHT}╚{'═' * 50}╝")
print()

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(("0.0.0.0", 5000))
server.listen()

log_server("Serveur en cours sur le port 5000", "SUCCESS")
log_server("En attente de connexions...", "INFO")

try:
    while True:
        client, address = server.accept()
        log_server(f"Nouvelle connexion depuis {address}", "INFO")
        threading.Thread(target=handle_client, args=(client,), daemon=True).start()
except KeyboardInterrupt:
    log_server("Arrêt du serveur...", "WARNING")
finally:
    server.close()
