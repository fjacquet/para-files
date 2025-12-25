#!/usr/bin/env python3
"""
Outil Chef Antoine - Conversion Markdown vers Paprika
Usage: python3 md_to_paprika.py <fichier.md> [--with-image <image_path>]

Crée un fichier .paprikarecipe (JSON gzippé) à partir d'un fichier Markdown.
Utilise Pydantic pour valider les données avant écriture.
"""
import base64
import gzip
import hashlib
import json
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path


try:
    from pydantic import BaseModel, Field, field_validator
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    print("⚠️  Pydantic non installé. Validation désactivée.")
    print("   Installer avec: pip install pydantic")


# ============================================================================
# MODÈLE PYDANTIC - Schéma Paprika 3
# ============================================================================

if PYDANTIC_AVAILABLE:
    class PaprikaRecipe(BaseModel):
        """Schéma validé pour un fichier .paprikarecipe"""

        # Champs requis
        name: str = Field(..., min_length=1, description="Nom de la recette avec emoji")
        ingredients: str = Field(..., min_length=1, description="Liste des ingrédients")
        directions: str = Field(..., min_length=1, description="Étapes de préparation")

        # Champs optionnels avec valeurs par défaut
        servings: str = Field(default="", description="Nombre de portions")
        source: str = Field(default="Chef Antoine - Cuisine Familiale")
        source_url: str = Field(default="")
        prep_time: str = Field(default="", description="Temps de préparation")
        cook_time: str = Field(default="", description="Temps de cuisson")
        total_time: str = Field(default="")
        categories: list[str] = Field(default_factory=list, description="Tags/catégories")
        nutritional_info: str = Field(default="", description="Informations nutritionnelles")
        difficulty: str = Field(default="", description="Niveau de difficulté")
        rating: int = Field(default=5, ge=0, le=5, description="Note sur 5")
        notes: str = Field(default="", description="Astuces du chef")
        description: str = Field(default="", description="Description courte")

        # Identifiants
        uid: str = Field(default_factory=lambda: str(uuid.uuid4()).upper())
        hash: str = Field(default="")
        created: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # Image
        photo: str | None = Field(default=None, description="Nom du fichier image")
        photo_data: str | None = Field(default=None, description="Image encodée en base64")

        @field_validator("name")
        @classmethod
        def name_not_empty(cls, v: str) -> str:
            if not v or v == "Recette sans nom":
                raise ValueError("Le nom de la recette est requis")
            return v

        @field_validator("ingredients")
        @classmethod
        def ingredients_not_empty(cls, v: str) -> str:
            if not v or len(v) < 10:
                raise ValueError("Les ingrédients sont requis (minimum 10 caractères)")
            return v

        @field_validator("directions")
        @classmethod
        def directions_not_empty(cls, v: str) -> str:
            if not v or len(v) < 10:
                raise ValueError("Les directions sont requises (minimum 10 caractères)")
            return v

        def generate_hash(self) -> None:
            """Génère le hash basé sur le contenu"""
            content = f"{self.name}{self.ingredients}{self.directions}{self.created}"
            self.hash = hashlib.sha256(content.encode()).hexdigest().upper()

        def to_paprika_dict(self) -> dict:
            """Convertit en dictionnaire pour JSON Paprika"""
            self.generate_hash()
            return self.model_dump()


# ============================================================================
# FONCTIONS DE PARSING MARKDOWN
# ============================================================================

def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter et retourne (metadata, body)"""
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    yaml_content = parts[1].strip()
    body = parts[2].strip()

    # Parse simple YAML (sans dépendance externe)
    metadata = {}
    current_key = None
    current_list = None

    for line in yaml_content.split("\n"):
        line = line.rstrip()
        if not line:
            continue

        # Liste item
        if line.startswith("  - "):
            if current_list is not None:
                current_list.append(line[4:].strip())
            continue

        # Nouvelle clé
        if ":" in line and not line.startswith(" "):
            if current_key and current_list is not None:
                metadata[current_key] = current_list

            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()

            if value:
                metadata[key] = value
                current_key = None
                current_list = None
            else:
                current_key = key
                current_list = []

    # Dernière liste
    if current_key and current_list is not None:
        metadata[current_key] = current_list

    return metadata, body


def extract_title(body: str) -> str:
    """Extrait le titre H1"""
    match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    return match.group(1).strip() if match else "Recette sans nom"


def extract_description(body: str) -> str:
    """Extrait la description (premier paragraphe après le titre)"""
    lines = body.split("\n")
    in_description = False
    description_lines = []

    for line in lines:
        if line.startswith("# "):
            in_description = True
            continue
        if in_description:
            if line.startswith("## ") or line.startswith("![["):
                break
            if line.strip():
                description_lines.append(line.strip())

    return " ".join(description_lines)


def extract_table_value(body: str, key: str) -> str:
    """Extrait une valeur d'un tableau Markdown"""
    pattern = rf"\*\*{re.escape(key)}\*\*\s*\|\s*(.+?)\s*\|?$"
    match = re.search(pattern, body, re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def extract_section(body: str, header: str) -> str:
    """Extrait le contenu d'une section (## header)"""
    pattern = rf"^##\s+{re.escape(header)}\s*$"
    match = re.search(pattern, body, re.MULTILINE | re.IGNORECASE)

    if not match:
        # Essayer avec regex plus souple
        pattern = rf"^##\s+{header}.*$"
        match = re.search(pattern, body, re.MULTILINE | re.IGNORECASE)

    if not match:
        return ""

    start = match.end()
    # Trouver la prochaine section
    next_section = re.search(r"^##\s+", body[start:], re.MULTILINE)
    end = start + next_section.start() if next_section else len(body)

    return body[start:end].strip()


def extract_ingredients(body: str) -> str:
    """Extrait les ingrédients"""
    section = extract_section(body, "Ingrédients")
    if not section:
        return ""

    lines = []
    for line in section.split("\n"):
        line = line.strip()
        if line.startswith("- "):
            lines.append(line)
        elif line.startswith("### "):
            lines.append(f"\n**{line[4:]}**")

    return "\n".join(lines)


def extract_directions(body: str) -> str:
    """Extrait les étapes de préparation"""
    section = extract_section(body, "Préparation")
    if not section:
        return ""

    lines = []

    for line in section.split("\n"):
        line = line.strip()
        if line.startswith("### "):
            # Sous-section (étape)
            lines.append(f"\n**{line[4:]}**")
        elif re.match(r"^\d+\.", line) or line.startswith("- "):
            lines.append(line)

    return "\n".join(lines)


def extract_notes(body: str) -> str:
    """Extrait les astuces/notes"""
    section = extract_section(body, "Astuces")
    if not section:
        return ""

    lines = []
    for line in section.split("\n"):
        line = line.strip()
        if line.startswith("- "):
            lines.append(line)

    return "\n".join(lines)


def extract_nutrition(body: str) -> str:
    """Extrait les informations nutritionnelles"""
    section = extract_section(body, "Nutrition")
    if not section:
        return ""

    lines = []
    for line in section.split("\n"):
        line = line.strip()
        if line.startswith("- "):
            # Nettoyer les emojis au début
            clean = re.sub(r"^-\s*[🔥💪🍞🧈]*\s*", "- ", line)
            lines.append(clean)

    return "\n".join(lines)


# ============================================================================
# FONCTION PRINCIPALE
# ============================================================================

def md_to_paprika(md_path: str, image_path: str = None) -> bool:
    """Convertit un fichier Markdown en fichier Paprika"""
    import shutil

    md_file = Path(md_path)
    if not md_file.exists():
        print(f"❌ Fichier non trouvé: {md_path}")
        return False

    # Lire le contenu
    content = md_file.read_text(encoding="utf-8")

    # Parser
    metadata, body = parse_frontmatter(content)

    # Extraire les données
    name = extract_title(body)
    description = extract_description(body)

    # Depuis le tableau d'informations
    servings = extract_table_value(body, "Portions")
    prep_time = extract_table_value(body, "Temps de préparation")
    cook_time = extract_table_value(body, "Temps de cuisson")
    difficulty = extract_table_value(body, "Difficulté")

    # Sections
    ingredients = extract_ingredients(body)
    directions = extract_directions(body)
    notes = extract_notes(body)
    nutritional_info = extract_nutrition(body)

    # Categories depuis les tags
    categories = metadata.get("tags", [])
    if isinstance(categories, str):
        categories = [categories]

    # Image
    photo = None
    photo_data = None
    if image_path:
        image_file = Path(image_path)
        if image_file.exists():
            # Nom de fichier basé sur la recette
            recipe_slug = md_file.stem  # ex: fondue-aux-bolets
            photo = f"{recipe_slug}.png"

            # Copier vers _media/ (si pas déjà là)
            media_dir = md_file.parent.parent / "_media"
            if not media_dir.exists():
                media_dir = md_file.parent / "_media"
            if media_dir.exists():
                dest_path = media_dir / photo
                # Éviter SameFileError si source == destination
                if image_file.resolve() != dest_path.resolve():
                    shutil.copy2(image_file, dest_path)
                    print(f"   📁 Image copiée: {dest_path}")
                else:
                    print(f"   📁 Image déjà en place: {dest_path}")

            # Encoder en base64
            with open(image_file, "rb") as f:
                photo_data = base64.b64encode(f.read()).decode("utf-8")

            # Ajouter WikiLink au Markdown si absent
            wikilink = f"![[{photo}]]"
            if wikilink not in content:
                # Insérer après le titre H1
                new_content = re.sub(
                    r"^(#\s+.+)$",
                    rf"\1\n\n{wikilink}",
                    content,
                    count=1,
                    flags=re.MULTILINE
                )
                if new_content != content:
                    md_file.write_text(new_content, encoding="utf-8")
                    print("   🔗 WikiLink ajouté au Markdown")

    # Construire et valider avec Pydantic si disponible
    if PYDANTIC_AVAILABLE:
        try:
            recipe = PaprikaRecipe(
                name=name,
                servings=servings,
                prep_time=prep_time,
                cook_time=cook_time,
                categories=categories,
                nutritional_info=nutritional_info,
                difficulty=difficulty,
                notes=notes,
                ingredients=ingredients,
                directions=directions,
                description=description,
                photo=photo,
                photo_data=photo_data
            )
            recipe_dict = recipe.to_paprika_dict()
        except Exception as e:
            print(f"❌ Validation échouée pour {md_file.name}:")
            print(f"   {e}")
            return False
    else:
        # Fallback sans validation
        uid = str(uuid.uuid4()).upper()
        hash_content = f"{name}{ingredients}{directions}{datetime.now().isoformat()}"
        hash_value = hashlib.sha256(hash_content.encode()).hexdigest().upper()

        recipe_dict = {
            "name": name,
            "servings": servings,
            "source": "Chef Antoine - Cuisine Familiale",
            "source_url": "",
            "prep_time": prep_time,
            "cook_time": cook_time,
            "total_time": "",
            "categories": categories,
            "nutritional_info": nutritional_info,
            "difficulty": difficulty,
            "rating": 5,
            "notes": notes,
            "ingredients": ingredients,
            "directions": directions,
            "description": description,
            "uid": uid,
            "hash": hash_value,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "photo": photo,
            "photo_data": photo_data
        }

    # Sauvegarder en .paprikarecipe (gzippé)
    paprika_path = md_file.with_suffix(".paprikarecipe")

    with gzip.open(paprika_path, "wt", encoding="utf-8") as f:
        json.dump(recipe_dict, f, ensure_ascii=False, indent=2)

    print(f"✅ {name}")
    print(f"   📄 Markdown: {md_file.name}")
    print(f"   📦 Paprika: {paprika_path.name}")
    if photo:
        print(f"   📷 Image: {photo}")

    return True


# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 md_to_paprika.py <fichier.md> [--with-image <image_path>]")
        print()
        print("Options:")
        print("  --with-image <path>  Inclure une image dans le fichier Paprika")
        print()
        print("Exemple:")
        print("  python3 md_to_paprika.py poulet-citron.md")
        print("  python3 md_to_paprika.py poulet-citron.md --with-image poulet.png")
        sys.exit(1)

    md_path = sys.argv[1]
    image_path = None

    if "--with-image" in sys.argv:
        idx = sys.argv.index("--with-image")
        if idx + 1 < len(sys.argv):
            image_path = sys.argv[idx + 1]

    success = md_to_paprika(md_path, image_path)
    sys.exit(0 if success else 1)
