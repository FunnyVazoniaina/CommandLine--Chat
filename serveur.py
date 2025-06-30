import socket
import threading
import json
import hashlib
import os

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

def handle_client(client_socket):
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
                return
        elif choice == "2":  # Inscription
            if pseudo in users:
                client_socket.send("PSEUDO_EXIST".encode())
                client_socket.close()
                return
            users[pseudo] = hash_password(password)
            save_users()
        else:
            client_socket.send("CHOIX_INVALIDE".encode())
            client_socket.close()
            return

        client_socket.send("AUTH_OK".encode())
        clients[client_socket] = pseudo
        pseudos.add(pseudo)
        broadcast(f"{pseudo} a rejoint le chat", client_socket)

        while True:
            msg = client_socket.recv(1024).decode()
            if msg == "/list":
                connected = ", ".join(pseudos)
                client_socket.send(f"Connectés: {connected}".encode())
            elif msg.startswith("/msg"):
                parts = msg.split(" ", 2)
                if len(parts) == 3:
                    dest_pseudo, message = parts[1], parts[2]
                    send_private(pseudo, dest_pseudo, message)
            else:
                broadcast(f"[{pseudo}] {msg}", client_socket)

    except:
        pass
    finally:
        pseudos.discard(clients.get(client_socket, ""))
        broadcast(f"{pseudo} a quitté le chat", client_socket)
        clients.pop(client_socket, None)
        client_socket.close()

def broadcast(message, sender):
    for client in clients:
        if client != sender:
            try:
                client.send(message.encode())
            except:
                pass

def send_private(from_user, to_user, message):
    for client, pseudo in clients.items():
        if pseudo == to_user:
            try:
                client.send(f"[Privé de {from_user}] {message}".encode())
            except:
                pass

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("0.0.0.0", 5000))
server.listen()
print("Serveur en cours sur le port 5000")

while True:
    client, _ = server.accept()
    threading.Thread(target=handle_client, args=(client,), daemon=True).start()
