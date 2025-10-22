import json
import customtkinter as ctk
from PIL import Image, ImageTk, ImageOps
import tkinter as tk
import threading
import cv2
import time
import os
from utils.montage import lancer_seance, set_camera, release_camera, get_frame_with_overlay
from utils.impression import imprimer_image
import pygame

class PhotoboothApp:
    def __init__(self, root):
        self.root = root
        self.config = self.load_config()
        self.button_color = self.config.get("button_color", "#1E90FF")
        self.root.title("Photobooth 💍")
        self.root.geometry("1000x1000")
        self.root.configure(fg_color=self.config.get("bg_color", "#F0F0F0"))
        self.bg_frame = ctk.CTkFrame(self.root, fg_color=self.config.get("bg_color", "#F0F0F0"), corner_radius=0)
        self.bg_frame.pack(fill="both", expand=True)

        pygame.mixer.init()
        self.son_bip = pygame.mixer.Sound("assets/bip.mp3")
        self.son_photo = pygame.mixer.Sound("assets/clickphoto.mp3")

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme(self.config.get("couleur_principale", "blue"))

        self.title_label = ctk.CTkLabel(
            self.bg_frame,
            text=self.config.get("titre_interface", "Photobooth - Template Mariage"),
            font=(self.config.get("font_titre", "Arial"), 28),
            text_color=self.config.get("couleur_titre", "black"),
            fg_color="transparent"
        )
        self.title_label.pack(pady=(20, 5))

        self.camera_label = ctk.CTkLabel(self.bg_frame, text="", fg_color="transparent")
        self.camera_label.place(relx=0.5, y=120, anchor="n")

        self.preview_label = ctk.CTkLabel(self.bg_frame, text="", fg_color="transparent")
        self.preview_label.place_forget()

        # Logo label
        self.logo_label = ctk.CTkLabel(self.bg_frame, text="", fg_color="transparent")
        self.logo_label.place_forget()

        logo_path = self.config.get("logo_path")
        if logo_path and os.path.exists(logo_path):
            logo_image = Image.open(logo_path).convert("RGBA")
            logo_width = self.config.get("logo_width", 300)
            logo_height = self.config.get("logo_height", 400)
            logo_image = logo_image.resize((logo_width, logo_height))
            self.logo_imgtk = ImageTk.PhotoImage(logo_image)
            self.logo_label.configure(image=self.logo_imgtk)

            logo_position = self.config.get("logo_position", "gauche")
            # Responsive placement using relx and anchor
            if logo_position == "gauche":
                self.logo_label.place(relx=0.0, x=10, y=130, anchor="nw")
            else:
                self.logo_label.place(relx=1.0, x=-(logo_width + 10), y=130, anchor="ne")

        self.button_frame = ctk.CTkFrame(self.bg_frame, fg_color="transparent")
        self.button_frame.pack(pady=10)

        self.start_button = ctk.CTkButton(self.button_frame, text="🎬 Lancer la séance photo", command=self.start_session, fg_color=self.button_color, text_color="white")
        self.start_button.grid(row=0, column=0, padx=10)

        self.print_button = ctk.CTkButton(self.button_frame, text="🖨️ Imprimer", command=self.imprimer_resultat, state="disabled", fg_color=self.button_color, text_color="white")
        self.print_button.grid(row=0, column=1, padx=10)

        self.reset_button = ctk.CTkButton(self.button_frame, text="🔁 Nouveau shooting", command=self.reset, state="disabled", fg_color=self.button_color, text_color="white")
        self.reset_button.grid(row=0, column=2, padx=10)

        set_camera()
        self.overlay_text = ""
        self.nom_fichier = ""
        self.result_imgtk = None
        self.create_admin_access_point()
        self.update_video()
        
    def create_admin_access_point(self):
        access_btn = ctk.CTkButton(self.button_frame, text="⚙️ Admin", width=80, height=30, command=self.ask_admin_password, fg_color=self.button_color, text_color="white")
        access_btn.grid(row=0, column=3, padx=10)

    def ask_admin_password(self):
        pw_win = ctk.CTkInputDialog(text="Mot de passe administrateur :", title="Accès admin")
        if pw_win.get_input() == self.config.get("mot_de_passe_admin"):
            self.open_admin_panel()

    def open_admin_panel(self):
        admin_win = ctk.CTkToplevel(self.root)
        admin_win.title("Panneau d'administration")
        admin_win.geometry("400x500")

        entries = {}

        def save_and_close():
            for key, entry in entries.items():
                val = entry.get() if not isinstance(entry, ctk.StringVar) else entry.get()
                if val.lower() in ["true", "false"]:
                    val = val.lower() == "true"
                elif val.isdigit():
                    val = int(val)
                self.config[key] = val
            with open("config.json", "w") as f:
                json.dump(self.config, f, indent=2)
            admin_win.destroy()

        row = 0
        for key in ["nombre_photos", "timer_seconds", "template", "texte_overlay", "impression_auto", "nombre_impressions", "duree_session_minutes"]:
            ctk.CTkLabel(admin_win, text=key.replace("_", " ").capitalize()).grid(row=row, column=0, padx=10, pady=5, sticky="e")
            if key == "template":
                import os
                templates_path = "templates"
                template_files = [f[:-5] for f in os.listdir(templates_path) if f.endswith(".json")]
                selected_template = ctk.StringVar(value=self.config.get("template", template_files[0] if template_files else ""))
                template_menu = ctk.CTkOptionMenu(admin_win, values=template_files, variable=selected_template)
                template_menu.grid(row=row, column=1, padx=10, pady=5)
                entries[key] = selected_template
            else:
                entry = ctk.CTkEntry(admin_win)
                entry.insert(0, str(self.config.get(key, "")))
                entry.grid(row=row, column=1, padx=10, pady=5)
                entries[key] = entry
            row += 1

        ctk.CTkLabel(admin_win, text="Titre de l'interface").grid(row=row, column=0, padx=10, pady=5, sticky="e")
        title_entry = ctk.CTkEntry(admin_win)
        title_entry.insert(0, self.config.get("titre_interface", "Photobooth - Template Mariage"))
        title_entry.grid(row=row, column=1, padx=10, pady=5)
        entries["titre_interface"] = title_entry
        row += 1

        ctk.CTkLabel(admin_win, text="Couleur principale").grid(row=row, column=0, padx=10, pady=5, sticky="e")
        color_entry = ctk.CTkEntry(admin_win)
        color_entry.insert(0, self.config.get("couleur_principale", "#0000FF"))
        color_entry.grid(row=row, column=1, padx=10, pady=5)
        entries["couleur_principale"] = color_entry
        row += 1

        ctk.CTkLabel(admin_win, text="Couleur de fond").grid(row=row, column=0, padx=10, pady=5, sticky="e")
        bg_color_entry = ctk.CTkEntry(admin_win)
        bg_color_entry.insert(0, self.config.get("bg_color", "#FFFFFF"))
        bg_color_entry.grid(row=row, column=1, padx=10, pady=5)
        entries["bg_color"] = bg_color_entry
        row += 1

        ctk.CTkLabel(admin_win, text="Police du titre").grid(row=row, column=0, padx=10, pady=5, sticky="e")
        font_options = ["Arial", "Helvetica", "Verdana", "Times", "Courier", "Comic Sans MS"]
        font_var = ctk.StringVar(value=self.config.get("font_titre", "Arial"))
        font_menu = ctk.CTkOptionMenu(admin_win, values=font_options, variable=font_var)
        font_menu.grid(row=row, column=1, padx=10, pady=5)
        entries["font_titre"] = font_var
        row += 1

        ctk.CTkLabel(admin_win, text="Couleur du titre").grid(row=row, column=0, padx=10, pady=5, sticky="e")
        color_font_entry = ctk.CTkEntry(admin_win)
        color_font_entry.insert(0, self.config.get("couleur_titre", "#000000"))
        color_font_entry.grid(row=row, column=1, padx=10, pady=5)
        entries["couleur_titre"] = color_font_entry
        row += 1

        # Ajout du champ couleur des boutons juste après "couleur_titre"
        ctk.CTkLabel(admin_win, text="Couleur des boutons").grid(row=row, column=0, padx=10, pady=5, sticky="e")
        button_color_entry = ctk.CTkEntry(admin_win)
        button_color_entry.insert(0, self.config.get("button_color", "#1E90FF"))
        button_color_entry.grid(row=row, column=1, padx=10, pady=5)
        entries["button_color"] = button_color_entry
        row += 1

        # --- Logo selection and positioning ---
        ctk.CTkLabel(admin_win, text="Logo (gauche/droite)").grid(row=row, column=0, padx=10, pady=5, sticky="e")
        logo_frame = ctk.CTkFrame(admin_win)
        logo_frame.grid(row=row, column=1, padx=10, pady=5)

        logo_path = ctk.StringVar(value=self.config.get("logo_path", ""))
        logo_pos = ctk.StringVar(value=self.config.get("logo_position", "gauche"))

        def choisir_logo():
            from tkinter import filedialog
            path = filedialog.askopenfilename(title="Sélectionner un logo", filetypes=[("Images", "*.png *.jpg *.jpeg")])
            if path:
                logo_path.set(path)
                logo_label.configure(text=os.path.basename(path))

        logo_button = ctk.CTkButton(logo_frame, text="📁 Choisir", command=choisir_logo, width=80)
        logo_button.pack(side="left", padx=(0, 5))

        logo_label = ctk.CTkLabel(logo_frame, text=os.path.basename(logo_path.get()) if logo_path.get() else "Aucun")
        logo_label.pack(side="left")

        entries["logo_path"] = logo_path
        entries["logo_position"] = logo_pos
        row += 1

        ctk.CTkOptionMenu(admin_win, values=["gauche", "droite"], variable=logo_pos).grid(row=row, column=1, padx=10, pady=5)
        row += 1

        # Ajout des champs largeur et hauteur du logo/photo
        ctk.CTkLabel(admin_win, text="Largeur de l'image (px)").grid(row=row, column=0, padx=10, pady=5, sticky="e")
        logo_width_entry = ctk.CTkEntry(admin_win)
        logo_width_entry.insert(0, str(self.config.get("logo_width", 300)))
        logo_width_entry.grid(row=row, column=1, padx=10, pady=5)
        entries["logo_width"] = logo_width_entry
        row += 1

        ctk.CTkLabel(admin_win, text="Hauteur de l'image (px)").grid(row=row, column=0, padx=10, pady=5, sticky="e")
        logo_height_entry = ctk.CTkEntry(admin_win)
        logo_height_entry.insert(0, str(self.config.get("logo_height", 400)))
        logo_height_entry.grid(row=row, column=1, padx=10, pady=5)
        entries["logo_height"] = logo_height_entry
        row += 1

        save_btn = ctk.CTkButton(admin_win, text="💾 Sauvegarder", command=save_and_close)
        save_btn.grid(row=row, columnspan=2, pady=20)

        def ajouter_template():
            from tkinter import filedialog, simpledialog
            nom_template = simpledialog.askstring("Nom du template", "Entrez un nom pour ce template :")
            if not nom_template:
                return
            json_path = filedialog.askopenfilename(title="Sélectionner le fichier JSON du template", filetypes=[("Fichiers JSON", "*.json")])
            image_path = filedialog.askopenfilename(title="Sélectionner l’image du template", filetypes=[("Images", "*.png *.jpg *.jpeg")])
            if json_path and image_path:
                os.makedirs("templates", exist_ok=True)
                import shutil
                shutil.copy(json_path, f"templates/{nom_template}.json")
                ext = os.path.splitext(image_path)[1]
                shutil.copy(image_path, f"templates/{nom_template}{ext}")
                template_menu.configure(values=[f[:-5] for f in os.listdir("templates") if f.endswith(".json")])
                selected_template.set(nom_template)

        ajouter_btn = ctk.CTkButton(admin_win, text="➕ Ajouter un template", command=ajouter_template)
        ajouter_btn.grid(row=row+1, columnspan=2, pady=10)

        def creer_template():
            template_win = ctk.CTkToplevel(self.root)
            template_win.title("Création d’un nouveau template")
            template_win.geometry("500x600")

            champs = {}

            ctk.CTkLabel(template_win, text="Nom du template").pack(pady=5)
            nom_entry = ctk.CTkEntry(template_win)
            nom_entry.pack(pady=5)

            img_path = [""]
            def choisir_image():
                from tkinter import filedialog
                path = filedialog.askopenfilename(title="Choisir une image fond", filetypes=[("Images", "*.png *.jpg *.jpeg")])
                img_path[0] = path
                if path:
                    img_label.configure(text=os.path.basename(path))

            ctk.CTkButton(template_win, text="🖼 Choisir l’image de fond", command=choisir_image).pack(pady=5)
            img_label = ctk.CTkLabel(template_win, text="Aucune image sélectionnée")
            img_label.pack()

            ctk.CTkLabel(template_win, text="Nombre de photos").pack(pady=5)
            nb_entry = ctk.CTkEntry(template_win)
            nb_entry.pack(pady=5)

            cadre_frame = ctk.CTkScrollableFrame(template_win, width=450, height=250)
            cadre_frame.pack(pady=10)

            def generer_champs():
                for widget in cadre_frame.winfo_children():
                    widget.destroy()
                try:
                    n = int(nb_entry.get())
                except:
                    return
                champs.clear()
                for i in range(n):
                    bloc = {}
                    ctk.CTkLabel(cadre_frame, text=f"Photo {i+1}").grid(row=i*2, column=0, columnspan=4, pady=(5,0))
                    for j, champ in enumerate(["x", "y", "width", "height"]):
                        ctk.CTkLabel(cadre_frame, text=champ).grid(row=i*2+1, column=j*2)
                        entry = ctk.CTkEntry(cadre_frame, width=40)
                        entry.grid(row=i*2+1, column=j*2+1, padx=2)
                        bloc[champ] = entry
                    champs[i] = bloc

            ctk.CTkButton(template_win, text="🛠 Générer les champs", command=generer_champs).pack(pady=5)

            def sauvegarder_template():
                nom = nom_entry.get()
                if not nom or not img_path[0] or not nb_entry.get():
                    return
                try:
                    n = int(nb_entry.get())
                except:
                    return
                cadres = []
                for i in range(n):
                    bloc = champs.get(i)
                    if not bloc: continue
                    try:
                        cadre = {k: int(bloc[k].get()) for k in bloc}
                        cadres.append(cadre)
                    except:
                        continue
                template_data = {
                    "nom": nom,
                    "image_fond": f"{nom}{os.path.splitext(img_path[0])[1]}",
                    "nombre_photos": n,
                    "cadres": cadres
                }
                os.makedirs("templates", exist_ok=True)
                import shutil
                shutil.copy(img_path[0], f"templates/{template_data['image_fond']}")
                with open(f"templates/{nom}.json", "w") as f:
                    json.dump(template_data, f, indent=2)
                template_menu.configure(values=[f[:-5] for f in os.listdir("templates") if f.endswith(".json")])
                selected_template.set(nom)
                template_win.destroy()

            ctk.CTkButton(template_win, text="💾 Enregistrer le template", command=sauvegarder_template).pack(pady=10)

        creer_btn = ctk.CTkButton(admin_win, text="🧩 Créer un template personnalisé", command=creer_template)
        creer_btn.grid(row=row+2, columnspan=2, pady=10)

    def load_template(self, nom_template):
        try:
            with open(f"templates/{nom_template}.json", "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Erreur chargement du template {nom_template} :", e)
            return None

    def update_video(self):
        frame = get_frame_with_overlay(self.overlay_text)
        if frame is not None:
            frame = cv2.resize(frame, (800, 500))
            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)
            self.camera_label.configure(image=imgtk)
            self.camera_label.imgtk = imgtk
        self.root.after(30, self.update_video)

    def start_session(self):
        self.start_button.configure(state="disabled")
        self.print_button.configure(state="disabled")
        self.reset_button.configure(state="disabled")
        self.preview_label.configure(image="")  # Clear preview
        self.camera_label.place(relx=0.5, y=120, anchor="n")
        self.preview_label.place_forget()
        threading.Thread(target=self.run_sequence).start()

    def run_sequence(self):
        self.overlay_text = ""
        template_name = self.config.get("template", "mariage")
        self.nom_fichier = self.get_unique_filename(template_name)
        template_data = self.load_template(template_name)
        # Afficher le loader centré
        loader_label.place(relx=0.5, rely=0.5, anchor="center")
        lancer_seance(template_data, self.set_overlay, self.nom_fichier)
        loader_label.destroy()
        self.afficher_preview()
        self.print_button.configure(state="normal")
        self.reset_button.configure(state="normal")

    def set_overlay(self, text):
        self.overlay_text = text
        if text == "__flash__":
            flash = ctk.CTkLabel(self.root, text="", width=self.root.winfo_width(), height=self.root.winfo_height(), fg_color="white")
            flash.place(relx=0.5, rely=0.5, anchor="center")
            self.root.after(150, flash.destroy)

    def afficher_preview(self):
        try:
            path = f"exports/{self.nom_fichier}.png"
            print(f"on ouvre :[{path}]")
            time.sleep(0.5)
            img = Image.open(path)
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()
            scale = min(window_width / img.width * 0.7, window_height / img.height * 0.7)
            new_size = (int(img.width * scale), int(img.height * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            # img_width, img_height = img.size
            self.result_imgtk = ImageTk.PhotoImage(img)
            self.camera_label.place_forget()
            self.preview_label.configure(image=self.result_imgtk)
            self.preview_label.place(relx=0.5, rely=0.5, anchor="center")
            self.fade_in(self.preview_label)
        except Exception as e:
            print("Erreur chargement preview :", e)

    def reset(self):
        self.start_button.configure(state="normal")
        self.print_button.configure(state="disabled")
        self.reset_button.configure(state="disabled")
        self.overlay_text = ""
        self.result_imgtk = None
        self.preview_label.configure(image="")
        self.preview_label.place_forget()
        self.camera_label.configure(image="")
        self.camera_label.place(relx=0.5, y=120, anchor="n")

    def imprimer_resultat(self):
        if self.nom_fichier:
            path = f"exports/{self.nom_fichier}.png"
            imprimer_image(path)

    def get_unique_filename(self, base):
        i = 1
        while os.path.exists(f"exports/{base}_{i}.png"):
            i += 1
        return f"{base}_{i}"

    def on_closing(self):
        release_camera()
        self.root.destroy()

    def fade_in(self, widget, step=0):
        if step > 10:
            return
        alpha = int(255 * (step / 10))
        widget.configure(fg_color=(0, 0, 0, alpha))  # simuler un fondu si possible
        self.root.after(30, lambda: self.fade_in(widget, step + 1))

    def load_config(self):
        try:
            with open("config.json", "r") as f:
                return json.load(f)
        except Exception as e:
            print("Erreur lors du chargement du fichier de configuration :", e)
            return {}

def main():
    root = ctk.CTk()

    def verifier_connexion():
        code = code_entry.get()
        config = {}
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
        except:
            pass

        if code == config.get("mot_de_passe_admin"):
            root.destroy()
            lancer_app(mode_admin=True)
        elif code == config.get("mot_de_passe_utilisateur"):
            root.destroy()
            lancer_app(mode_admin=False)
        else:
            error_label.configure(text="❌ Code incorrect", text_color="red")

    root.geometry("400x200")
    root.title("Connexion")

    ctk.CTkLabel(root, text="🔐 Entrez le code d’accès :", font=("Arial", 18)).pack(pady=20)
    code_entry = ctk.CTkEntry(root, show="*")
    code_entry.pack(pady=10)
    ctk.CTkButton(root, text="Se connecter", command=verifier_connexion).pack(pady=10)
    error_label = ctk.CTkLabel(root, text="")
    error_label.pack()

    root.mainloop()

def lancer_app(mode_admin=False):
    app_root = ctk.CTk()
    app = PhotoboothApp(app_root)
    app_root.protocol("WM_DELETE_WINDOW", app.on_closing)
    if not mode_admin:
        app.button_frame.grid_slaves(row=0, column=3)[0].grid_forget()  # Masquer bouton admin
    app_root.mainloop()

if __name__ == "__main__":
    main()