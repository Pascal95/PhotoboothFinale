from PIL import Image
import subprocess

def imprimer_image(path_image, nom_imprimante="Canon_SELPHY_CP1500"):
    try:
        image = Image.open(path_image)
        image = image.convert("RGB")  # au cas où c’est JPEG
        temp_path = "print_ready.png"
        image.save(temp_path, format="PNG")
        subprocess.run(["lp", "-d", nom_imprimante, temp_path], check=True)
        print("✅ Impression lancée avec succès.")
    except Exception as e:
        print(f"❌ Erreur pendant l’impression : {e}")