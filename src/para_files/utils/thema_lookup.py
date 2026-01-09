"""THEMA code lookup service for book classification.

Maps book subjects and keywords to official THEMA (Thema v1.6) classification codes.
THEMA is the international book classification standard used in publishing.

See: https://www.editeur.org/151/Thema/
"""

from __future__ import annotations

import re
from functools import lru_cache

from para_files.taxonomies.loader import get_taxonomy_loader
from para_files.taxonomies.models import ThemaCode, ThemaTaxonomy


# =============================================================================
# Subject to THEMA Code Mappings
# =============================================================================

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
    "political philosophy": "QDTS",
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
    "medieval history": "NHCC",
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


# =============================================================================
# THEMA Lookup Service
# =============================================================================


class ThemaLookup:
    """Service for looking up THEMA codes from book subjects."""

    def __init__(self, taxonomy: ThemaTaxonomy | None = None) -> None:
        """Initialize the lookup service.

        Args:
            taxonomy: Optional pre-loaded ThemaTaxonomy. If None, loads from config.
        """
        self._taxonomy = taxonomy

    @property
    def taxonomy(self) -> ThemaTaxonomy:
        """Get the THEMA taxonomy (lazy-loaded)."""
        if self._taxonomy is None:
            loader = get_taxonomy_loader()
            self._taxonomy = loader.load_thema()
        return self._taxonomy

    def lookup_subject(self, subject: str) -> str | None:
        """Find THEMA code for a single subject.

        Args:
            subject: Book subject string (e.g., "DevOps", "Python programming").

        Returns:
            THEMA code (e.g., "UMZ") or None if no match.
        """
        subject_lower = subject.lower().strip()

        # Direct lookup
        if subject_lower in SUBJECT_TO_THEMA:
            return SUBJECT_TO_THEMA[subject_lower]

        # Try partial matching for compound subjects
        for key, code in SUBJECT_TO_THEMA.items():
            if key in subject_lower or subject_lower in key:
                return code

        return None

    def lookup_subjects(self, subjects: list[str]) -> str | None:
        """Find best THEMA code from a list of subjects.

        Tries each subject and returns the most specific (longest) code found.

        Args:
            subjects: List of book subjects.

        Returns:
            Best matching THEMA code or None.
        """
        if not subjects:
            return None

        best_code: str | None = None
        best_specificity = 0

        for subject in subjects:
            code = self.lookup_subject(subject)
            # Prefer more specific codes (longer = more specific in THEMA)
            if code and len(code) > best_specificity:
                best_code = code
                best_specificity = len(code)

        return best_code

    def lookup_from_text(self, text: str) -> str | None:
        """Extract THEMA code from free text (title, description).

        Scans text for known subject keywords.

        Args:
            text: Free text to analyze.

        Returns:
            Best matching THEMA code or None.
        """
        if not text:
            return None

        text_lower = text.lower()
        candidates: list[tuple[str, int]] = []  # (code, specificity)

        for keyword, code in SUBJECT_TO_THEMA.items():
            # Use word boundary matching
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, text_lower):
                candidates.append((code, len(code)))

        if not candidates:
            return None

        # Return most specific code
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def get_code_info(self, code: str) -> ThemaCode | None:
        """Get full THEMA code information.

        Args:
            code: THEMA code value (e.g., "UMZ").

        Returns:
            ThemaCode with description and hierarchy info, or None.
        """
        return self.taxonomy.get_code(code)

    def get_hierarchy(self, code: str) -> list[ThemaCode]:
        """Get full hierarchy from root to given code.

        Args:
            code: THEMA code value.

        Returns:
            List of ThemaCode from root to target.
        """
        return self.taxonomy.get_hierarchy(code)

    def build_para_path(self, code: str) -> str:
        """Build PARA path from THEMA code.

        Args:
            code: THEMA code value.

        Returns:
            PARA path like "3_Resources/livres/U_Informatique/UB_Programmation"
        """
        return self.taxonomy.build_para_path(code)


# =============================================================================
# Convenience Functions
# =============================================================================


@lru_cache(maxsize=1)
def get_thema_lookup() -> ThemaLookup:
    """Get cached ThemaLookup instance."""
    return ThemaLookup()


def lookup_thema_code(subjects: list[str]) -> str | None:
    """Convenience function to lookup THEMA code from subjects.

    Args:
        subjects: List of book subjects.

    Returns:
        THEMA code or None.
    """
    return get_thema_lookup().lookup_subjects(subjects)


def thema_to_para_path(code: str) -> str:
    """Convenience function to convert THEMA code to PARA path.

    Args:
        code: THEMA code value.

    Returns:
        PARA path string.
    """
    return get_thema_lookup().build_para_path(code)
