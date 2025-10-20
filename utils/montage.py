# Nouveau montage.py adapté pour webcam en liveview et Canon pour capture photo
import cv2
import time
from PIL import Image
import os
import pygame
import subprocess
from datetime import datetime

camera = None

def set_camera():
    global camera
    camera = cv2.VideoCapture(0)  # Logitech webcam (assume /dev/video0 ou index 0)


def release_camera():
    global camera
    if camera:
        camera.release()


def get_frame_with_overlay(overlay_text=""):
    global camera
    if not camera:
        return None
    ret, frame = camera.read()
    if not ret:
        return None
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    if overlay_text:
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(frame, overlay_text, (200, 100), font, 3, (255, 255, 255), 5, cv2.LINE_AA)
    return frame


def capture_photo():
    # Pour vérifier le format d'image supporté par l'appareil, utiliser :
    # gphoto2 --get-config imageformat
    # Unmount volume s'il est monté (optionnel mais préférable)
    subprocess.run([
        "gio", "mount", "-u", "gphoto2://Canon_Inc._Canon_Digital_Camera/"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        subprocess.run([
            "gphoto2",
            "--set-config", "output=Off",
            "--set-config", "capturetarget=1",
            "--trigger-capture"
        ], check=True)

        time.sleep(2)  # temps pour que le fichier s'enregistre dans la mémoire interne

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"photo_{timestamp}.png"

        subprocess.run([
            "gphoto2",
            "--wait-event-and-download=FILEADDED",
            "--filename", filename
        ], check=True)

        img = Image.open(filename).convert("RGB")
        img.save(filename, format="PNG")  # Conversion sans perte
        return img
    except Exception as e:
        print(f"Erreur capture : {e}")
        return None


def lancer_seance(template_data, overlay_callback, nom_fichier="resultat"):
    pygame.mixer.init()
    son_bip = pygame.mixer.Sound("assets/bip.mp3")
    son_photo = pygame.mixer.Sound("assets/clickphoto.mp3")

    template_path = f"templates/{template_data['image_fond']}"
    template = Image.open(template_path).convert("RGBA")
    photos = []
    nombre_photos = template_data.get("nombre_photos", 4)
    cadres = template_data.get("cadres", [])

    for i in range(nombre_photos):
        for sec in range(5, 0, -1):
            overlay_callback(str(sec))
            if sec in [2, 1]:
                try:
                    son_bip.play()
                except:
                    pass
            time.sleep(1)
        overlay_callback("__flash__")
        time.sleep(0.15)
        overlay_callback("")
        try:
            son_photo.play()
        except:
            pass

        img = capture_photo()
        if img is not None:
            photos.append(img)
            print(f"Photo {i+1} capturée ✅")
        else:
            print(f"Photo {i+1} échouée ❌")
        time.sleep(1)

    for i, photo in enumerate(photos):
        if i >= len(cadres):
            print(f"Aucun cadre défini pour la photo {i+1}, sautée.")
            continue
        cadre = cadres[i]
        photo_resized = photo.resize((cadre["width"], cadre["height"]), Image.Resampling.LANCZOS)
        template.paste(photo_resized, (cadre["x"], cadre["y"]))

    output_path = f"exports/{nom_fichier}.png"
    template.convert("RGB").save(output_path)
    print(f"✅ Montage sauvegardé : {output_path}")