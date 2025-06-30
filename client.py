import socket
import threading

def receive(sock):
    while True:
        try:
            msg = sock.recv(1024).decode()
            print(msg)
        except:
            print("Déconnecté du serveur")
            sock.close()
            break

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("127.0.0.1", 5000))

# Interface de connexion / inscription
choice = input("Tapez 1 pour se connecter, 2 pour s'inscrire: ")
pseudo = input("Votre pseudo: ")
password = input("Mot de passe: ")

print(client.recv(1024).decode())  # demande choix
client.send(choice.encode())
print(client.recv(1024).decode())  # demande pseudo
client.send(pseudo.encode())
print(client.recv(1024).decode())  # demande mot de passe
client.send(password.encode())

response = client.recv(1024).decode()
if response == "PSEUDO_EXIST":
    print("Ce pseudo existe déjà.")
    client.close()
elif response != "AUTH_OK":
    print("Authentification échouée.")
    client.close()
else:
    print("Connecté au chat ! Tapez vos messages (/msg, /list, /exit)")
    threading.Thread(target=receive, args=(client,), daemon=True).start()
    while True:
        msg = input()
        if msg == "/exit":
            client.close()
            break
        client.send(msg.encode())
