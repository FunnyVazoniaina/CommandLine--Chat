import socket
import threading

def receive(sock):
    while True:
        try:
            msg = sock.recv(1024).decode()
            print(msg)
        except:
            print("Déconnecté du serveur.")
            sock.close()
            break

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("127.0.0.1", 5000))

pseudo = input("Votre pseudo : ")
password = input("Mot de passe : ")

print(client.recv(1024).decode())  # "Pseudo: "
client.send(pseudo.encode())
print(client.recv(1024).decode())  # "Mot de passe: "
client.send(password.encode())

response = client.recv(1024).decode()
if response != "AUTH_OK":
    print("Authentification échouée.")
    client.close()
else:
    print("Connecté ! Tapez vos messages.")
    threading.Thread(target=receive, args=(client,), daemon=True).start()
    while True:
        msg = input()
        if msg == "/exit":
            client.close()
            break
        client.send(msg.encode())
