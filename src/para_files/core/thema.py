"""Thema book subjects (spec §4.1): subject keywords to a Thema code, and a code to folders.

Only the Thema level-1 and level-2 folder names ship, in ``data/thema_l1l2.json``, generated
once from Thema v1.6. Thema codes are prefix-hierarchical, so a code's level-1 and level-2
ancestors are its first one and two characters.
"""

from __future__ import annotations

import json
import re
from functools import cache
from importlib.resources import files


COMPUTING_SUBJECT_MAP: dict[str, str] = {
    # General computing
    "computer science": "UY",
    "computing": "U",
    "informatique": "U",
    "information technology": "U",
    # Software Engineering & DevOps
    "devops": "UMZ",  # Software engineering (closest match)
    "software engineering": "UMZ",
    "génie logiciel": "UMZ",
    "software development": "UM",
    "continuous integration": "UMZ",
    "continuous delivery": "UMZ",
    "ci/cd": "UMZ",
    # Programming
    "programming": "UM",
    "programmation": "UM",
    "python": "UMX",  # Programming languages
    "java": "UMX",
    "javascript": "UMX",
    "typescript": "UMX",
    "go": "UMX",
    "golang": "UMX",
    "rust": "UMX",
    "c++": "UMX",
    "c programming": "UMX",
    # Agile & Methodologies
    "agile": "UMF",
    "scrum": "UMF",
    "extreme programming": "UMH",
    "xp": "UMH",
    # Web Development
    "web development": "UMW",
    "web programming": "UMW",
    "web services": "UMWS",
    "react": "UMW",
    "angular": "UMW",
    "vue": "UMW",
    "node.js": "UMW",
    "nodejs": "UMW",
    # Mobile Development
    "mobile development": "UMS",
    "android": "UMS",
    "ios development": "UMS",
    "swift": "UMS",
    "kotlin": "UMS",
    # Databases
    "database": "UMT",
    "databases": "UMT",
    "sql": "UMT",
    "nosql": "UMT",
    "mongodb": "UMT",
    "postgresql": "UMT",
    "mysql": "UMT",
    "oracle database": "UMT",
    # Cloud & Infrastructure
    "cloud computing": "UTC",
    "cloud": "UTC",
    "aws": "UTC",
    "amazon web services": "UTC",
    "azure": "UTC",
    "google cloud": "UTC",
    "gcp": "UTC",
    # Containers & Orchestration
    "kubernetes": "UT",  # Systems analysis & design
    "k8s": "UT",
    "docker": "UT",
    "containers": "UT",
    "containerization": "UT",
    "openshift": "UT",
    # AI & Machine Learning
    "artificial intelligence": "UYQ",
    "machine learning": "UYQM",
    "deep learning": "UYQM",
    "neural networks": "UYQM",
    "natural language processing": "UYQM",
    "nlp": "UYQM",
    "computer vision": "UYQM",
    # Security
    "computer security": "UR",
    "cybersecurity": "UR",
    "network security": "UR",
    "information security": "UR",
    "cryptography": "URY",
    # Networking
    "computer networks": "UT",
    "networking": "UT",
    "network administration": "UT",
    # Systems & Architecture
    "operating systems": "UL",
    "linux": "ULP",
    "unix": "ULP",
    "windows": "ULP",
    "system administration": "UT",
    # Data Science
    "data science": "UYQ",
    "data analysis": "UYQ",
    "big data": "UYQ",
    "data engineering": "UYQ",
}

BUSINESS_SUBJECT_MAP: dict[str, str] = {
    "business": "K",
    "management": "KJ",
    "project management": "KJM",
    "leadership": "KJL",
    "entrepreneurship": "KJH",
    "marketing": "KJS",
    "finance": "KF",
    "economics": "KC",
    "accounting": "KFC",
}

# Science & Technology (P*, T* codes)
SCIENCE_SUBJECT_MAP: dict[str, str] = {
    # Mathematics
    "mathematics": "PB",
    "mathématiques": "PB",
    # Physics
    "physics": "PH",
    "physique": "PH",
    # Chemistry
    "chemistry": "PN",
    "chimie": "PN",
    # Biology
    "biology": "PS",
    "biologie": "PS",
    # Engineering & Technology
    "engineering": "T",
    "ingénierie": "T",
    # Electronics & Electrical Engineering (TJ codes)
    "electronics": "TJ",
    "électronique": "TJ",
    "electronic engineering": "TJF",
    "génie électronique": "TJF",
    "microprocessor": "TJF",  # Digital electronics
    "microprocessors": "TJF",
    "microcontroller": "TJF",
    "microcontrollers": "TJF",
    "digital logic": "TJFC",
    "circuit": "TJFC",
    "circuits": "TJFC",
    "embedded systems": "TJF",
    "semiconductor": "TJF",
    # Electrical Engineering (THR code)
    "electrical engineering": "THR",
    "electrotechnique": "THR",
}

# Humanities & Philosophy (Q* codes)  # noqa: ERA001
HUMANITIES_SUBJECT_MAP: dict[str, str] = {
    # Philosophy
    "philosophy": "QD",
    "philosophie": "QD",
    "ethics": "QDTQ",
    "éthique": "QDTQ",
    "moral philosophy": "QDTQ",
    "metaphysics": "QDTJ",
    "métaphysique": "QDTJ",
    "epistemology": "QDTK",
    "épistémologie": "QDTK",
    "logic": "QDTL",
    "logique": "QDTL",
    "aesthetics": "QDTN",
    "esthétique": "QDTN",
    "political philosophy": "QDTS",
    "philosophie politique": "QDTS",
    "ancient philosophy": "QDHA",
    "greek philosophy": "QDHA",
    "western philosophy": "QDHR",
    # Religion
    "religion": "Q",
    "theology": "QR",
    "théologie": "QR",
}

# Social Sciences & Politics (J* codes)
SOCIAL_SCIENCE_SUBJECT_MAP: dict[str, str] = {
    # Social Sciences
    "social science": "J",
    "social sciences": "J",
    "sciences sociales": "J",
    "sociology": "JH",
    "sociologie": "JH",
    "anthropology": "JH",
    "anthropologie": "JH",
    "cultural studies": "JBCC",
    "études culturelles": "JBCC",
    "popular culture": "JBCC1",
    # Politics
    "politics": "JP",
    "politique": "JP",
    "political": "JP",  # Broad match for political topics
    "political science": "JPA",
    "science politique": "JPA",
    "political theory": "JPA",
    "théorie politique": "JPA",
    "political thought": "JPA",
    "government": "JP",
    "gouvernement": "JP",
    "political tradition": "JPA",
    "political history": "JPA",
    "public policy": "JPP",
    "international relations": "JPS",
    "relations internationales": "JPS",
    # Famous political philosophers (helps classify books by these thinkers)
    "hobbes": "JPA",
    "locke": "JPA",
    "rousseau": "JPA",
    "machiavelli": "JPA",
    "habermas": "JPA",
    "rawls": "JPA",
    "marx": "JPA",
    "montesquieu": "JPA",
    # Education
    "education": "JN",
    "éducation": "JN",
    "pedagogy": "JN",
    "pédagogie": "JN",
    # Psychology
    "psychology": "JM",
    "psychologie": "JM",
    "social psychology": "JMH",
    "psychologie sociale": "JMH",
    "communication": "JMHC",
}

# Arts & Literature (A*, D*, F* codes)
ARTS_LITERATURE_SUBJECT_MAP: dict[str, str] = {
    # Arts
    "art": "A",
    "arts": "A",
    "art history": "AGA",
    "histoire de l'art": "AGA",
    "visual arts": "AF",
    "arts visuels": "AF",
    "performing arts": "AFKP",
    "arts du spectacle": "AFKP",
    "photography": "AJ",
    "photographie": "AJ",
    "design": "AK",
    "architecture": "AM",
    "music": "AV",
    "musique": "AV",
    "cinema": "ATFN",
    "cinéma": "ATFN",
    "film": "ATFN",
    "television": "ATFN",
    "télévision": "ATFN",
    "theatre": "AT",
    "théâtre": "AT",
    # Literature & Writing
    "literature": "D",
    "littérature": "D",
    "literary studies": "DS",
    "études littéraires": "DS",
    "creative writing": "WQ",
    "écriture créative": "WQ",
    "storytelling": "DN",  # True stories / narrative
    "narration": "DN",
    "narrative": "DN",
    "récit": "DN",
    "poetry": "DC",
    "poésie": "DC",
    "drama": "DD",
    # Fiction
    "fiction": "F",
    "novel": "F",
    "roman": "F",
    "science fiction": "FL",
    "science-fiction": "FL",
    "sci-fi": "FL",
    "fantasy": "FM",
    "thriller": "FH",
    "historical fiction": "FV",
}

# History & Geography (N* codes)  # noqa: ERA001
HISTORY_SUBJECT_MAP: dict[str, str] = {
    "history": "NH",
    "histoire": "NH",
    "world history": "NH",
    "ancient history": "NHC",
    "medieval history": "NH",  # Thema has no medieval-history code; NHCC did not exist
    "modern history": "NHD",
    "military history": "NHW",
    "biography": "DN",
    "biographie": "DN",
    "autobiography": "DNB",
    "autobiographie": "DNB",
    "geography": "RG",
    "géographie": "RG",
}

# Combined mapping
SUBJECT_TO_THEMA: dict[str, str] = {
    **COMPUTING_SUBJECT_MAP,
    **BUSINESS_SUBJECT_MAP,
    **SCIENCE_SUBJECT_MAP,
    **HUMANITIES_SUBJECT_MAP,
    **SOCIAL_SCIENCE_SUBJECT_MAP,
    **ARTS_LITERATURE_SUBJECT_MAP,
    **HISTORY_SUBJECT_MAP,
}


@cache
def _folders() -> dict[str, str]:
    """Thema level-1 and level-2 code -> folder name, e.g. 'UB' -> 'UB_Themes_generaux'."""
    text = files("para_files").joinpath("data/thema_l1l2.json").read_text(encoding="utf-8")
    table: dict[str, str] = json.loads(text)
    return table


@cache
def _whole(phrase: str) -> re.Pattern[str]:
    """`phrase` as a whole word or phrase: no letter, digit, underscore or hyphen next to it."""
    return re.compile(rf"(?<![\w-]){re.escape(phrase)}(?![\w-])")


@cache
def lookup_subject(subject: str) -> str | None:
    """Thema code for one subject: exact keyword, else the longest key found in it as a word."""
    wanted = subject.lower().strip()
    if not wanted:
        return None
    if wanted in SUBJECT_TO_THEMA:
        return SUBJECT_TO_THEMA[wanted]
    matches = [code for key, code in SUBJECT_TO_THEMA.items() if _whole(key).search(wanted)]
    return max(matches, key=len, default=None)


def lookup_thema_code(subjects: list[str]) -> str | None:
    """The most specific (longest) Thema code any subject maps to; the first wins a tie."""
    best: str | None = None
    for subject in subjects:
        code = lookup_subject(subject)
        if code and len(code) > len(best or ""):
            best = code
    return best


def thema_folders(code: str) -> str | None:
    """Level-1 and level-2 folders below the library, or None for a code not in the table.

    E.g. 'UB' -> 'U_Informatique_et_technologies_de/UB_Themes_generaux'.
    """
    table = _folders()
    names = [table[prefix] for prefix in dict.fromkeys((code[:1], code[:2])) if prefix in table]
    return "/".join(names) if code[:1] in table else None
