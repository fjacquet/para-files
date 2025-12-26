#!/usr/bin/env python3
"""
Outil Chef Antoine - Intégration d'image dans une recette Paprika
Usage: python3 integrate_image.py <image_path> <recipe_name> [--notes "astuces"]
"""

import base64
import gzip
import json
import re
import shutil
import sys
from pathlib import Path


# Chemins de base
VAULT_ROOT = Path("/Users/fjacquet/Documents/Second Brain")
RECETTES_ROOT = VAULT_ROOT / "3_Resources/recettes"
MEDIA_PATH = RECETTES_ROOT / "_media"


def find_recipe_path(recipe_name: str) -> Path | None:
    """Trouve le chemin du fichier .paprikarecipe"""
    for paprika_file in RECETTES_ROOT.rglob(f"{recipe_name}.paprikarecipe"):
        return paprika_file
    return None


def integrate_image(image_path: str, recipe_name: str, notes: str = None):
    """Intègre une image dans un fichier .paprikarecipe et met à jour le .md"""

    image_file = Path(image_path)
    if not image_file.exists():
        print(f"❌ Image non trouvée: {image_path}")
        return False

    # Trouver le fichier paprikarecipe
    paprika_path = find_recipe_path(recipe_name)
    if not paprika_path:
        print(f"❌ Recette non trouvée: {recipe_name}")
        return False

    md_path = paprika_path.with_suffix(".md")
    media_dest = MEDIA_PATH / f"{recipe_name}.png"

    # 1. Lire le JSON existant
    with gzip.open(paprika_path, "rt", encoding="utf-8") as f:
        recipe = json.load(f)

    # 2. Encoder l'image en base64
    with open(image_file, "rb") as f:
        photo_base64 = base64.b64encode(f.read()).decode("utf-8")

    # 3. Copier l'image dans _media (sauf si déjà en place)
    if image_file.resolve() != media_dest.resolve():
        shutil.copy(image_file, media_dest)

    # 4. Mettre à jour le JSON
    recipe["photo_data"] = photo_base64
    if notes:
        recipe["notes"] = notes

    # 5. Sauvegarder le .paprikarecipe
    with gzip.open(paprika_path, "wt", encoding="utf-8") as f:
        json.dump(recipe, f, ensure_ascii=False, indent=2)

    # 6. Mettre à jour le fichier .md (ajouter l'image si absente)
    if md_path.exists():
        with open(md_path, encoding="utf-8") as f:
            content = f.read()

        image_ref = f"![[{recipe_name}.png]]"
        if image_ref not in content:
            # Ajouter après le titre
            content = re.sub(r"(# .+\n)", f"\\1\n{image_ref}\n", content, count=1)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(content)

    print(f"✅ {recipe_name}")
    print(f"   📷 Image: {media_dest.name}")
    print(f"   📄 Paprika: {paprika_path.name}")
    if md_path.exists():
        print(f"   📝 Markdown: {md_path.name}")

    return True


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 integrate_image.py <image_path> <recipe_name> [--notes 'astuces']")
        sys.exit(1)

    image_path = sys.argv[1]
    recipe_name = sys.argv[2]
    notes = None

    if "--notes" in sys.argv:
        notes_idx = sys.argv.index("--notes")
        if notes_idx + 1 < len(sys.argv):
            notes = sys.argv[notes_idx + 1]

    success = integrate_image(image_path, recipe_name, notes)
    sys.exit(0 if success else 1)
