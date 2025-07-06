import subprocess
import os

def imprimer_image(path_image, nom_imprimante="Canon_SELPHY_CP1500"):
    try:
        if not os.path.exists(path_image):
            print(f"❌ Fichier non trouvé : {path_image}")
            return
        subprocess.run(["lp", "-d", nom_imprimante, path_image], check=True)
        print("✅ Impression lancée avec succès.")
    except Exception as e:
        print(f"❌ Erreur pendant l’impression : {e}")