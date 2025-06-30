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

# Nouvelles structures pour les rooms et blocages
rooms = {"general": set()}  # room_name: set of pseudos
client_rooms = {}  # socket: room_name
blocked_users = {}  # pseudo: set of blocked_pseudos

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

def create_room(room_name, creator_pseudo):
    """Crée une nouvelle room"""
    if room_name not in rooms:
        rooms[room_name] = set()
        log_server(f"Room '{room_name}' créée par {creator_pseudo}", "SUCCESS")
        return True
    return False

def join_room(client_socket, room_name, pseudo):
    """Fait rejoindre un utilisateur à une room"""
    # Quitter l'ancienne room
    old_room = client_rooms.get(client_socket, "general")
    if old_room in rooms:
        rooms[old_room].discard(pseudo)
        if old_room != "general" and len(rooms[old_room]) == 0:
            # Supprimer la room si elle est vide (sauf general)
            del rooms[old_room]
            log_server(f"Room '{old_room}' supprimée (vide)", "INFO")
    
    # Rejoindre la nouvelle room
    if room_name not in rooms:
        rooms[room_name] = set()
    
    rooms[room_name].add(pseudo)
    client_rooms[client_socket] = room_name
    log_server(f"{pseudo} a rejoint la room '{room_name}'", "INFO")
    return True

def get_room_users(room_name):
    """Retourne la liste des utilisateurs dans une room"""
    return list(rooms.get(room_name, set()))

def is_user_blocked(sender_pseudo, receiver_pseudo):
    """Vérifie si un utilisateur est bloqué"""
    return receiver_pseudo in blocked_users.get(sender_pseudo, set())

def block_user(blocker_pseudo, blocked_pseudo):
    """Bloque un utilisateur"""
    if blocker_pseudo not in blocked_users:
        blocked_users[blocker_pseudo] = set()
    blocked_users[blocker_pseudo].add(blocked_pseudo)
    log_server(f"{blocker_pseudo} a bloqué {blocked_pseudo}", "INFO")

def unblock_user(blocker_pseudo, blocked_pseudo):
    """Débloque un utilisateur"""
    if blocker_pseudo in blocked_users:
        blocked_users[blocker_pseudo].discard(blocked_pseudo)
        log_server(f"{blocker_pseudo} a débloqué {blocked_pseudo}", "INFO")
        return True
    return False

def cleanup_disconnected_client(client_socket):
    """Nettoie un client déconnecté"""
    if client_socket in clients:
        pseudo = clients[client_socket]
        pseudos.discard(pseudo)
        
        # Retirer de la room
        if client_socket in client_rooms:
            room_name = client_rooms[client_socket]
            if room_name in rooms:
                rooms[room_name].discard(pseudo)
            del client_rooms[client_socket]
            
        del clients[client_socket]
        
    try:
        client_socket.close()
    except:
        pass

def broadcast_to_room(room_name, message, sender_socket=None):
    """Diffuse un message à tous les clients d'une room spécifique"""
    if room_name not in rooms:
        return
        
    disconnected = []
    room_users = rooms[room_name].copy()
    
    for client_socket, pseudo in clients.items():
        if pseudo in room_users and client_socket != sender_socket:
            # Vérifier si l'utilisateur n'a pas bloqué l'expéditeur
            sender_pseudo = clients.get(sender_socket, "")
            if sender_pseudo and not is_user_blocked(pseudo, sender_pseudo):
                try:
                    client_socket.send(message.encode())
                except:
                    disconnected.append(client_socket)
    
    # Nettoyer les clients déconnectés
    for client in disconnected:
        cleanup_disconnected_client(client)

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
        
        # Rejoindre la room générale par défaut
        join_room(client_socket, "general", pseudo)
        
        # Message de bienvenue avec horodatage
        welcome_msg = f"SYSTEM:{format_timestamp()} Bienvenue {pseudo}! Vous êtes dans la room 'general'. Tapez /help pour voir les commandes"
        client_socket.send(welcome_msg.encode())
        
        broadcast_to_room("general", f"SYSTEM:{format_timestamp()} {pseudo} a rejoint le chat", client_socket)
        log_server(f"{pseudo} s'est connecté", "SUCCESS")

        while True:
            msg = client_socket.recv(1024).decode()
            if not msg:
                break
                
            if msg == "/list":
                current_room = client_rooms.get(client_socket, "general")
                room_users = get_room_users(current_room)
                response = f"SYSTEM:{format_timestamp()} Room '{current_room}' - Connectés ({len(room_users)}): {', '.join(room_users)}"
                client_socket.send(response.encode())
                
            elif msg == "/rooms":
                room_list = []
                for room_name, users_set in rooms.items():
                    room_list.append(f"{room_name} ({len(users_set)} users)")
                response = f"SYSTEM:{format_timestamp()} Rooms disponibles: {', '.join(room_list)}"
                client_socket.send(response.encode())
                
            elif msg == "/help":
                help_text = f"""HELP:{format_timestamp()} 📋 COMMANDES DISPONIBLES:
/help - Afficher cette aide
/list - Lister les utilisateurs de la room actuelle
/rooms - Lister toutes les rooms disponibles
/create <room> - Créer une nouvelle room
/join <room> - Rejoindre une room existante
/leave - Retourner à la room générale
/msg <user> <message> - Envoyer un message privé
/block <user> - Bloquer un utilisateur
/unblock <user> - Débloquer un utilisateur
/blocked - Voir la liste des utilisateurs bloqués
/quit - Quitter le chat"""
                client_socket.send(help_text.encode())
                
            elif msg.startswith("/create "):
                room_name = msg[8:].strip()
                if room_name and room_name.isalnum():
                    if create_room(room_name, pseudo):
                        join_room(client_socket, room_name, pseudo)
                        response = f"SYSTEM:{format_timestamp()} Room '{room_name}' créée et rejointe avec succès"
                        client_socket.send(response.encode())
                    else:
                        error_msg = f"ERROR:{format_timestamp()} La room '{room_name}' existe déjà"
                        client_socket.send(error_msg.encode())
                else:
                    error_msg = f"ERROR:{format_timestamp()} Nom de room invalide (utilisez uniquement lettres et chiffres)"
                    client_socket.send(error_msg.encode())
                    
            elif msg.startswith("/join "):
                room_name = msg[6:].strip()
                if room_name in rooms:
                    old_room = client_rooms.get(client_socket, "general")
                    join_room(client_socket, room_name, pseudo)
                    
                    # Notifier l'ancienne room
                    broadcast_to_room(old_room, f"SYSTEM:{format_timestamp()} {pseudo} a quitté la room", client_socket)
                    # Notifier la nouvelle room
                    broadcast_to_room(room_name, f"SYSTEM:{format_timestamp()} {pseudo} a rejoint la room", client_socket)
                    
                    response = f"SYSTEM:{format_timestamp()} Vous avez rejoint la room '{room_name}'"
                    client_socket.send(response.encode())
                else:
                    error_msg = f"ERROR:{format_timestamp()} La room '{room_name}' n'existe pas. Utilisez /create pour la créer"
                    client_socket.send(error_msg.encode())
                    
            elif msg == "/leave":
                current_room = client_rooms.get(client_socket, "general")
                if current_room != "general":
                    broadcast_to_room(current_room, f"SYSTEM:{format_timestamp()} {pseudo} a quitté la room", client_socket)
                    join_room(client_socket, "general", pseudo)
                    broadcast_to_room("general", f"SYSTEM:{format_timestamp()} {pseudo} a rejoint la room générale", client_socket)
                    response = f"SYSTEM:{format_timestamp()} Vous êtes retourné à la room générale"
                    client_socket.send(response.encode())
                else:
                    error_msg = f"ERROR:{format_timestamp()} Vous êtes déjà dans la room générale"
                    client_socket.send(error_msg.encode())
                    
            elif msg.startswith("/block "):
                blocked_pseudo = msg[7:].strip()
                if blocked_pseudo in pseudos and blocked_pseudo != pseudo:
                    block_user(pseudo, blocked_pseudo)
                    response = f"SYSTEM:{format_timestamp()} Utilisateur '{blocked_pseudo}' bloqué"
                    client_socket.send(response.encode())
                else:
                    error_msg = f"ERROR:{format_timestamp()} Utilisateur '{blocked_pseudo}' introuvable ou invalide"
                    client_socket.send(error_msg.encode())
                    
            elif msg.startswith("/unblock "):
                unblocked_pseudo = msg[9:].strip()
                if unblock_user(pseudo, unblocked_pseudo):
                    response = f"SYSTEM:{format_timestamp()} Utilisateur '{unblocked_pseudo}' débloqué"
                    client_socket.send(response.encode())
                else:
                    error_msg = f"ERROR:{format_timestamp()} Utilisateur '{unblocked_pseudo}' n'était pas bloqué"
                    client_socket.send(error_msg.encode())
                    
            elif msg == "/blocked":
                blocked_list = list(blocked_users.get(pseudo, set()))
                if blocked_list:
                    response = f"SYSTEM:{format_timestamp()} Utilisateurs bloqués: {', '.join(blocked_list)}"
                else:
                    response = f"SYSTEM:{format_timestamp()} Aucun utilisateur bloqué"
                client_socket.send(response.encode())
                
            elif msg.startswith("/msg"):
                parts = msg.split(" ", 2)
                if len(parts) == 3:
                    dest_pseudo, message = parts[1], parts[2]
                    if not is_user_blocked(dest_pseudo, pseudo):  # Vérifier si on n'est pas bloqué
                        if send_private(pseudo, dest_pseudo, message):
                            # Confirmer l'envoi à l'expéditeur
                            confirm_msg = f"PRIVATE_SENT:{format_timestamp()} Message privé envoyé à {dest_pseudo}: {message}"
                            client_socket.send(confirm_msg.encode())
                            log_server(f"Message privé de {pseudo} vers {dest_pseudo}")
                        else:
                            error_msg = f"ERROR:{format_timestamp()} Utilisateur '{dest_pseudo}' introuvable"
                            client_socket.send(error_msg.encode())
                    else:
                        error_msg = f"ERROR:{format_timestamp()} Vous êtes bloqué par cet utilisateur"
                        client_socket.send(error_msg.encode())
                else:
                    error_msg = f"ERROR:{format_timestamp()} Usage: /msg <utilisateur> <message>"
                    client_socket.send(error_msg.encode())
                    
            elif msg == "/quit":
                break
                
            else:
                # Message public dans la room actuelle
                current_room = client_rooms.get(client_socket, "general")
                public_msg = f"PUBLIC:{format_timestamp()} [{pseudo}] {msg}"
                broadcast_to_room(current_room, public_msg, client_socket)
                log_server(f"[{pseudo}@{current_room}] {msg}")

    except Exception as e:
        log_server(f"Erreur avec le client {pseudo}: {e}", "ERROR")
    finally:
        # Nettoyage lors de la déconnexion
        current_room = client_rooms.get(client_socket, "general")
        pseudos.discard(pseudo)
        
        if client_socket in client_rooms:
            rooms[current_room].discard(pseudo)
            del client_rooms[client_socket]
            
        if pseudo:
            broadcast_to_room(current_room, f"SYSTEM:{format_timestamp()} {pseudo} a quitté le chat", client_socket)
            log_server(f"{pseudo} s'est déconnecté", "WARNING")
            
        clients.pop(client_socket, None)
        client_socket.close()

def broadcast(message, sender):
    """Diffuse un message à tous les clients sauf l'expéditeur (fonction legacy)"""
    current_room = client_rooms.get(sender, "general")
    broadcast_to_room(current_room, message, sender)

# Démarrage du serveur avec interface améliorée
print(f"{Fore.GREEN + Style.BRIGHT}╔{'═' * 50}╗")
print(f"{Fore.GREEN + Style.BRIGHT}║{' ' * 8}SERVEUR MESSAGERIE AVEC ROOMS{' ' * 9}║")
print(f"{Fore.GREEN + Style.BRIGHT}╚{'═' * 50}╝")
print()

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(("0.0.0.0", 5000))
server.listen()

log_server("Serveur en cours sur le port 5000", "SUCCESS")
log_server("Room 'general' créée par défaut", "INFO")
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
