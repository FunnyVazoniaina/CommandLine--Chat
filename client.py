import socket
import threading
import os
from datetime import datetime
from colorama import init, Fore, Back, Style

# Initialiser colorama pour Windows
init(autoreset=True)

def play_notification_sound():
    """Joue un son de notification pour les messages privés"""
    try:
        # Son système simple (compatible multi-plateforme)
        if os.name == 'nt':  # Windows
            import winsound
            winsound.Beep(1000, 200)
        else:  # Linux/Mac
            os.system('echo -e "\a"')
    except:
        # Fallback: caractère de bell
        print('\a', end='', flush=True)

def format_timestamp():
    """Retourne l'horodatage formaté"""
    return datetime.now().strftime("[%H:%M]")

def print_welcome():
    """Affiche le message de bienvenue avec style"""
    os.system('clear' if os.name != 'nt' else 'cls')
    print(Fore.CYAN + Style.BRIGHT + "╔" + "═" * 58 + "╗")
    print(Fore.CYAN + Style.BRIGHT + "║" + " " * 12 + "MESSAGERIE TERMINAL ROOMS" + " " * 19 + "║")
    print(Fore.CYAN + Style.BRIGHT + "╚" + "═" * 58 + "╝")
    print()

def print_separator():
    """Affiche une ligne de séparation"""
    print(Fore.CYAN + "─" * 60)

def format_message(msg_type, content, extra=""):
    """Formate les messages selon leur type avec couleurs"""
    if msg_type == "PRIVATE":
        play_notification_sound()  # Son pour message privé
        return f"{Fore.MAGENTA}🔒 {content}"
    elif msg_type == "PRIVATE_SENT":
        return f"{Fore.CYAN}🔒 {content}"
    elif msg_type == "PUBLIC":
        return f"{Fore.WHITE}{content}"
    elif msg_type == "SYSTEM":
        return f"{Fore.YELLOW}ℹ️  {content}"
    elif msg_type == "ERROR":
        return f"{Fore.RED}❌ {content}"
    elif msg_type == "HELP":
        return f"{Fore.GREEN}{content}"
    else:
        return content

def print_help():
    """Affiche l'aide des commandes disponibles"""
    help_text = f"""
{Fore.YELLOW + Style.BRIGHT}📋 COMMANDES DISPONIBLES:

{Fore.CYAN + Style.BRIGHT}💬 CHAT GÉNÉRAL:
{Fore.GREEN}┌─────────────────────────────────────────────────────────┐
{Fore.GREEN}│ /help              - Afficher cette aide               │
{Fore.GREEN}│ /list              - Lister les utilisateurs connectés │
{Fore.GREEN}│ /msg <user> <msg>  - Envoyer un message privé          │
{Fore.GREEN}│ /quit              - Quitter la messagerie             │
{Fore.GREEN}│ /clear             - Effacer l'écran                   │
{Fore.GREEN}└─────────────────────────────────────────────────────────┘

{Fore.CYAN + Style.BRIGHT}🏠 GESTION DES ROOMS:
{Fore.GREEN}┌─────────────────────────────────────────────────────────┐
{Fore.GREEN}│ /rooms             - Lister toutes les rooms           │
{Fore.GREEN}│ /create <room>     - Créer une nouvelle room           │
{Fore.GREEN}│ /join <room>       - Rejoindre une room existante      │
{Fore.GREEN}│ /leave             - Retourner à la room générale      │
{Fore.GREEN}└─────────────────────────────────────────────────────────┘

{Fore.CYAN + Style.BRIGHT}🚫 GESTION DES BLOCAGES:
{Fore.GREEN}┌─────────────────────────────────────────────────────────┐
{Fore.GREEN}│ /block <user>      - Bloquer un utilisateur            │
{Fore.GREEN}│ /unblock <user>    - Débloquer un utilisateur          │
{Fore.GREEN}│ /blocked           - Voir les utilisateurs bloqués     │
{Fore.GREEN}└─────────────────────────────────────────────────────────┘

{Fore.YELLOW}💡 EXEMPLES:
{Fore.CYAN}   /create gaming     {Fore.WHITE}→ Crée la room "gaming"
{Fore.CYAN}   /join gaming       {Fore.WHITE}→ Rejoint la room "gaming"  
{Fore.CYAN}   /block spammer     {Fore.WHITE}→ Bloque l'utilisateur "spammer"
    """
    print(help_text)

def receive(sock):
    """Thread pour recevoir les messages du serveur"""
    while True:
        try:
            msg = sock.recv(1024).decode()
            if not msg:
                break
                
            # Parser les différents types de messages
            if msg.startswith("PRIVATE:"):
                content = msg[8:]  # Enlever "PRIVATE:"
                print(format_message("PRIVATE", content))
                
            elif msg.startswith("PRIVATE_SENT:"):
                content = msg[13:]  # Enlever "PRIVATE_SENT:"
                print(format_message("PRIVATE_SENT", content))
                
            elif msg.startswith("PUBLIC:"):
                content = msg[7:]  # Enlever "PUBLIC:"
                print(format_message("PUBLIC", content))
                
            elif msg.startswith("SYSTEM:"):
                content = msg[7:]  # Enlever "SYSTEM:"
                print(format_message("SYSTEM", content))
                
            elif msg.startswith("ERROR:"):
                content = msg[6:]  # Enlever "ERROR:"
                print(format_message("ERROR", content))
                
            elif msg.startswith("HELP:"):
                content = msg[5:]  # Enlever "HELP:"
                print(format_message("HELP", content))
                
            else:
                # Message par défaut
                print(format_message("SYSTEM", msg))
                
        except Exception as e:
            print(format_message("ERROR", f"Erreur de réception: {e}"))
            sock.close()
            break

def show_room_examples():
    """Affiche des exemples d'utilisation des rooms"""
    examples = f"""
{Fore.YELLOW + Style.BRIGHT}🏠 EXEMPLES D'UTILISATION DES ROOMS:

{Fore.CYAN}Créer une room pour discuter de gaming:
{Fore.WHITE}   /create gaming

{Fore.CYAN}Rejoindre une room existante:
{Fore.WHITE}   /join gaming

{Fore.CYAN}Voir qui est dans votre room actuelle:
{Fore.WHITE}   /list

{Fore.CYAN}Voir toutes les rooms disponibles:
{Fore.WHITE}   /rooms

{Fore.CYAN}Retourner à la room générale:
{Fore.WHITE}   /leave

{Fore.GREEN}💡 Les rooms sont parfaites pour organiser des discussions thématiques !
    """
    print(examples)

# Interface de bienvenue
print_welcome()

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    client.connect(("127.0.0.1", 5000))
    print(format_message("SYSTEM", f"{format_timestamp()} Connecté au serveur"))
except Exception as e:
    print(format_message("ERROR", f"Impossible de se connecter: {e}"))
    exit()

# Interface de connexion / inscription
print(f"{Fore.CYAN}Choisissez une option:")
print(f"{Fore.GREEN}1 - Se connecter")
print(f"{Fore.GREEN}2 - S'inscrire")
print_separator()

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
    print(format_message("ERROR", "Ce pseudo existe déjà."))
    client.close()
elif response == "AUTH_FAIL":
    print(format_message("ERROR", "Authentification échouée."))
    client.close()
elif response == "CHOIX_INVALIDE":
    print(format_message("ERROR", "Choix invalide."))
    client.close()
elif response != "AUTH_OK":
    print(format_message("ERROR", "Erreur de connexion."))
    client.close()
else:
    print(format_message("SYSTEM", f"{format_timestamp()} Connecté au chat !"))
    print(format_message("SYSTEM", "Tapez /help pour voir toutes les commandes disponibles"))
    print(format_message("SYSTEM", "Tapez /examples pour voir des exemples d'utilisation des rooms"))
    print_separator()
    
    # Démarrer le thread de réception
    threading.Thread(target=receive, args=(client,), daemon=True).start()
    
    try:
        while True:
            msg = input().strip()
            
            if not msg:
                continue
                
            # Gérer les commandes locales
            if msg == "/help":
                print_help()
                continue
            elif msg == "/examples":
                show_room_examples()
                continue
            elif msg == "/clear":
                print_welcome()
                print(format_message("SYSTEM", "Écran effacé"))
                print_separator()
                continue
            elif msg == "/quit":
                print(format_message("SYSTEM", f"{format_timestamp()} Déconnexion..."))
                client.send(msg.encode())
                break
            
            # Envoyer le message au serveur
            client.send(msg.encode())
            
    except KeyboardInterrupt:
        print(f"\n{format_message('SYSTEM', f'{format_timestamp()} Déconnexion...')}")
    except EOFError:
        print(f"\n{format_message('SYSTEM', f'{format_timestamp()} Déconnexion...')}")
    finally:
        client.close()
