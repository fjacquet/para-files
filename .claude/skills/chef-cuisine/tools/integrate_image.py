"""
Outil Chef Antoine - Integration d'image dans une recette Paprika.

Usage: python3 integrate_image.py <image_path> <recipe_name> [--notes "astuces"]
"""

from __future__ import annotations

import base64
import gzip
import json
import logging
import re
import shutil
import sys
from pathlib import Path


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Chemins de base
VAULT_ROOT = Path("/Users/fjacquet/Documents/Second Brain")
RECETTES_ROOT = VAULT_ROOT / "3_Resources/recettes"
MEDIA_PATH = RECETTES_ROOT / "_media"

# Constants
MIN_ARGS_COUNT = 3


def find_recipe_path(recipe_name: str) -> Path | None:
    """Trouve le chemin du fichier .paprikarecipe."""
    for paprika_file in RECETTES_ROOT.rglob(f"{recipe_name}.paprikarecipe"):
        return paprika_file
    return None


def integrate_image(image_path: str, recipe_name: str, notes: str | None = None) -> bool:
    """Integre une image dans un fichier .paprikarecipe et met a jour le .md."""
    image_file = Path(image_path)
    if not image_file.exists():
        logger.error("Image non trouvee: %s", image_path)
        return False

    # Trouver le fichier paprikarecipe
    paprika_path = find_recipe_path(recipe_name)
    if not paprika_path:
        logger.error("Recette non trouvee: %s", recipe_name)
        return False

    md_path = paprika_path.with_suffix(".md")
    media_dest = MEDIA_PATH / f"{recipe_name}.png"

    # 1. Lire le JSON existant
    with gzip.open(paprika_path, "rt", encoding="utf-8") as f:
        recipe = json.load(f)

    # 2. Encoder l'image en base64
    with image_file.open("rb") as f:
        photo_base64 = base64.b64encode(f.read()).decode("utf-8")

    # 3. Copier l'image dans _media (sauf si deja en place)
    if image_file.resolve() != media_dest.resolve():
        shutil.copy(image_file, media_dest)

    # 4. Mettre a jour le JSON
    recipe["photo_data"] = photo_base64
    if notes:
        recipe["notes"] = notes

    # 5. Sauvegarder le .paprikarecipe
    with gzip.open(paprika_path, "wt", encoding="utf-8") as f:
        json.dump(recipe, f, ensure_ascii=False, indent=2)

    # 6. Mettre a jour le fichier .md (ajouter l'image si absente)
    if md_path.exists():
        with md_path.open(encoding="utf-8") as f:
            content = f.read()

        image_ref = f"![[{recipe_name}.png]]"
        if image_ref not in content:
            # Ajouter apres le titre
            content = re.sub(r"(# .+\n)", f"\\1\n{image_ref}\n", content, count=1)
            with md_path.open("w", encoding="utf-8") as f:
                f.write(content)

    logger.info("Recette: %s", recipe_name)
    logger.info("  Image: %s", media_dest.name)
    logger.info("  Paprika: %s", paprika_path.name)
    if md_path.exists():
        logger.info("  Markdown: %s", md_path.name)

    return True


if __name__ == "__main__":
    if len(sys.argv) < MIN_ARGS_COUNT:
        logger.info(
            "Usage: python3 integrate_image.py <image_path> <recipe_name> [--notes 'astuces']"
        )
        sys.exit(1)

    arg_image_path = sys.argv[1]
    arg_recipe_name = sys.argv[2]
    arg_notes: str | None = None

    if "--notes" in sys.argv:
        notes_idx = sys.argv.index("--notes")
        if notes_idx + 1 < len(sys.argv):
            arg_notes = sys.argv[notes_idx + 1]

    success = integrate_image(arg_image_path, arg_recipe_name, arg_notes)
    sys.exit(0 if success else 1)
