# main_dslr.py

import tkinter as tk
from PIL import Image, ImageTk
import subprocess, uuid, os, time

class DSLRPhotoBooth:
    def __init__(self, root):
        self.root = root
        self.root.title("DSLR PhotoBooth")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Label pour la preview de la dernière photo
        self.preview_label = tk.Label(root, text="Aucune photo", bg="black", fg="white")
        self.preview_label.pack(fill="both", expand=True)

        # Bouton capture
        self.btn_capture = tk.Button(root, text="📷 Prendre une photo", command=self.capture_photo)
        self.btn_capture.pack(pady=10)

        # Dossier de sauvegarde
        os.makedirs("captures", exist_ok=True)

    def capture_photo(self):
        """Prend une photo avec gphoto2 et l'affiche."""
        filename = f"captures/photo_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
        cmd = ["gphoto2", "--capture-image-and-download", "--filename", filename]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            tk.messagebox.showerror("Erreur DSLR", f"Impossible de capturer la photo :\n{e}")
            return

        # Charge et affiche la photo capturée
        img = Image.open(filename)
        # Redimensionne pour la fenêtre
        w = self.preview_label.winfo_width() or 800
        h = self.preview_label.winfo_height() or 600
        img = img.copy().thumbnail((w, h), Image.ANTIALIAS) or img
        self.imgtk = ImageTk.PhotoImage(img)
        self.preview_label.configure(image=self.imgtk, text="")

        print(f"Photo enregistrée → {filename}")

    def on_close(self):
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("800x600")
    app = DSLRPhotoBooth(root)
    root.mainloop()