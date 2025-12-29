"""Filename sanitization utilities.

Provides functions to sanitize strings for safe use in filenames across
different operating systems (Windows, macOS, Linux).

Invalid/restricted characters handled:
- , (comma) - can cause issues in some systems
- # (hash) - can cause URL encoding issues
- " (double quote) - invalid on Windows
- * (asterisk) - invalid on Windows
- : (colon) - invalid on Windows, used for drive letters
- < (less than) - invalid on Windows
- > (greater than) - invalid on Windows
- ? (question mark) - invalid on Windows
- / (forward slash) - path separator on Unix
- \\ (backslash) - path separator on Windows
- | (pipe) - invalid on Windows
"""

from __future__ import annotations

import re


# Characters that are invalid or restricted in filenames
# Windows forbidden: < > : " / \ | ? *
# Additional for safety: , #
INVALID_FILENAME_CHARS = r'[,#"*:<>?/\\|]'

# Compiled regex for performance
_INVALID_CHARS_PATTERN = re.compile(INVALID_FILENAME_CHARS)
_WHITESPACE_PATTERN = re.compile(r"\s+")
_MULTIPLE_UNDERSCORES = re.compile(r"_+")


def sanitize_filename(
    name: str,
    replacement: str = "_",
    max_length: int | None = None,
    *,
    preserve_extension: bool = False,
) -> str:
    """Sanitize a string for safe use as a filename.

    Replaces invalid characters and whitespace with the replacement character.
    Optionally truncates to a maximum length.

    Args:
        name: Original string to sanitize.
        replacement: Character to replace invalid chars with (default: "_").
        max_length: Maximum length of result (None = unlimited).
        preserve_extension: If True and max_length set, preserve file extension.

    Returns:
        Sanitized filename-safe string.

    Examples:
        >>> sanitize_filename("Hello: World")
        'Hello_World'
        >>> sanitize_filename("File/Name#Test")
        'File_Name_Test'
        >>> sanitize_filename("My File.pdf", max_length=10, preserve_extension=True)
        'My_Fil.pdf'
    """
    if not name:
        return name

    # Replace invalid characters
    safe = _INVALID_CHARS_PATTERN.sub(replacement, name)

    # Replace whitespace with replacement char
    safe = _WHITESPACE_PATTERN.sub(replacement, safe)

    # Normalize multiple replacement chars to single
    if replacement == "_":
        safe = _MULTIPLE_UNDERSCORES.sub("_", safe)

    # Strip leading/trailing replacement chars
    safe = safe.strip(replacement)

    # Handle max length
    if max_length and len(safe) > max_length:
        if preserve_extension:
            # Try to preserve extension
            parts = safe.rsplit(".", 1)
            has_extension = len(parts) > 1
            if has_extension and len(parts[1]) < max_length - 1:
                ext = parts[1]
                name_part = parts[0][: max_length - len(ext) - 1]
                # Try to break at word/underscore boundary
                if "_" in name_part:
                    name_part = name_part.rsplit("_", 1)[0]
                safe = f"{name_part}.{ext}"
            else:
                safe = safe[:max_length]
        else:
            # Try to break at word boundary
            safe = safe[:max_length]
            if "_" in safe:
                safe = safe.rsplit("_", 1)[0]

    return safe


def sanitize_path_component(
    name: str,
    replacement: str = "-",
    *,
    replace_spaces: bool = False,
) -> str:
    """Sanitize a string for use as a path component (directory name).

    More aggressive than sanitize_filename - also replaces & with 'et'
    for better readability in French contexts.

    Args:
        name: Original string to sanitize.
        replacement: Character to replace invalid chars with (default: "-").
        replace_spaces: If True, replace spaces with replacement char (for filenames).

    Returns:
        Sanitized path-safe string.

    Examples:
        >>> sanitize_path_component("Arts : généralités")
        'Arts - généralités'
        >>> sanitize_path_component("Art & Design")
        'Art et Design'
        >>> sanitize_path_component("New York", replacement="_", replace_spaces=True)
        'New_York'
    """
    if not name:
        return name

    # Replace & with 'et' (common in French)
    safe = name.replace("&", "et")

    # Replace invalid characters
    safe = _INVALID_CHARS_PATTERN.sub(replacement, safe)

    if replace_spaces:
        # Replace whitespace with replacement char (for filename-like behavior)
        safe = _WHITESPACE_PATTERN.sub(replacement, safe)
        # Normalize multiple replacement chars
        if replacement == "_":
            safe = _MULTIPLE_UNDERSCORES.sub("_", safe)
        elif replacement == "-":
            safe = re.sub(r"-+", "-", safe)
    else:
        # Normalize multiple replacement chars
        if replacement == "-":
            safe = re.sub(r"-+", "-", safe)
        elif replacement == "_":
            safe = _MULTIPLE_UNDERSCORES.sub("_", safe)

        # Normalize whitespace around replacement
        safe = re.sub(rf"\s*{re.escape(replacement)}\s*", f" {replacement} ", safe)
        safe = _WHITESPACE_PATTERN.sub(" ", safe)

    # Strip leading/trailing
    return safe.strip(f" {replacement}")


def is_valid_filename(name: str) -> bool:
    """Check if a string contains any invalid filename characters.

    Args:
        name: String to check.

    Returns:
        True if the string is safe for use as a filename.
    """
    if not name:
        return False
    return not bool(_INVALID_CHARS_PATTERN.search(name))


def get_invalid_chars(name: str) -> list[str]:
    """Get list of invalid characters found in a string.

    Args:
        name: String to check.

    Returns:
        List of invalid characters found (may contain duplicates).
    """
    return _INVALID_CHARS_PATTERN.findall(name)
