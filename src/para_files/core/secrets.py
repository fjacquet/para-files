"""Secrets guard (spec §4.3): files that must never leave the machine or be moved."""

from __future__ import annotations

import re


_NAME = re.compile(
    r"credential|passw|secret|token|api[_-]?key|login"
    r"|recovery[_ -]?(?:phrase|code|key)|seed[_ -]?phrase"
    r"|licen[cs]e[_ -]?(?:key|string|code)"
    r"|mots?[_ -]?de[_ -]?passe|(?<![a-z])mdp(?![a-z])"
    r"|identifiants(?![_ -]?(?:tva|fiscaux|fiscal))"
    r"|id_(?:rsa|dsa|ecdsa|ed25519)(?!\.pub)|^\.netrc$|\.(?:pem|p12|pfx|kdbx)$"
    r"|^\.env(?:\.[\w-]+)*$|\.env$",
    re.IGNORECASE,
)
_TEXT: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY(?: BLOCK)?-----")),
    ("cloud_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("vault_keys", re.compile(r'"(?:root_token|(?:unseal|recovery)_keys(?:_b64|_hex)?)"\s*:')),
    (
        "recovery_phrase",
        re.compile(r"\b(?:recovery|seed|mnemonic)\s+(?:phrase|words?)\b", re.IGNORECASE),
    ),
    (
        "credential_value",
        re.compile(
            r"^[^\S\n]*(?:[\w.'-]+[^\S\n]+){0,3}?[\"']?[\w.-]*"
            r"(?:password|passwd|pwd|secret|token|api[_-]?key"
            r"|mots?[^\S\n]+de[^\S\n]+passe|(?<![a-z])mdp(?![a-z])"
            r"|(?<![a-z])identifiants(?![a-z]))"
            r"[\w.-]{0,60}[\"']?[^\S\n]*"
            r"[:=][^\S\n]*(?:\r?\n[^\S\n]*)?(?!https?://(?![^\s/]*:[^\s/@]*@))\S{4,}[^\S\n]*$",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
)


def secret_reason(name: str, text: str = "") -> str | None:
    """Return why a file looks secret ("name" or a content pattern id), else None.

    Values shorter than 4 characters do not count, so settings such as a switch's
    password-policy lines (``passwdcfg.minlength: 8``) pass. A content value must sit on the
    same line as its label and must not be a URL, so a bare "Password:" heading or a reset link
    is not a secret. Logins are usernames: ``login`` is a name marker only, never a content one.
    """
    if _NAME.search(name):
        return "name"
    for reason, pattern in _TEXT:
        if pattern.search(text):
            return reason
    return None
