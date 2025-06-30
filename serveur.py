import socket
import threading
import json

clients = {}  # socket: pseudo
pseudos = set()

with open("users.json", "r") as f:
    users = json.load(f)

def handle_client(client_socket):
    try:
        client_socket.send("Pseudo: ".encode())
        pseudo = client_socket.recv(1024).decode()

        client_socket.send("Mot de passe: ".encode())
        password = client_socket.recv(1024).decode()

        if pseudo not in users or users[pseudo] != password or pseudo in pseudos:
            client_socket.send("AUTH_FAIL".encode())
            client_socket.close()
            return

        client_socket.send("AUTH_OK".encode())
        clients[client_socket] = pseudo
        pseudos.add(pseudo)
        broadcast(f"{pseudo} a rejoint le chat", client_socket)

        while True:
            msg = client_socket.recv(1024).decode()
            if msg.startswith("/msg"):
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
print("Serveur lancé sur le port 5000")

while True:
    client, _ = server.accept()
    threading.Thread(target=handle_client, args=(client,)).start()
