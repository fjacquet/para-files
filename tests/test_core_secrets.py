"""Tests for the secrets guard (spec §4.3, S8)."""

from __future__ import annotations

import pytest

from para_files.core.secrets import secret_reason


SWITCH_POLICY = "passwdcfg.minlength: 8\npasswdcfg.oldpasswd: 1\npasswdcfg.lockoutduration: 30\n"


@pytest.mark.parametrize(
    "name",
    [
        "wallet_recovery_phrase.txt",
        "s3-credentials.json",
        "portal_login.txt",
        "license-string.txt",
        "id_rsa",
        "server.pem",
        "vault.kdbx",
        "API_KEY.txt",
        "Mots de passe.txt",
        "mdp_banque.txt",
        "identifiants.txt",
        ".env",
        "prod.env",
        ".netrc",
        "id_ecdsa",
        ".env.local",
        ".env.production",
    ],
)
def test_secret_names_are_flagged(name):
    assert secret_reason(name) == "name"


@pytest.mark.parametrize(
    "name",
    [
        "2026-01-23_acme_facture.pdf",
        "Bulletin salaire 2019.pdf",
        "vendor-cyber-recovery-overview.pptx",
        "rack-front.jpg",
        "identifiant_fiscal.pdf",
        "commande.pdf",
        "envelope.env.pdf",
        "environment.pdf",
    ],
)
def test_ordinary_names_pass(name):
    assert secret_reason(name, "Invoice total CHF 49.90") is None


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("-----BEGIN OPENSSH PRIVATE KEY-----\nabc", "private_key"),
        ("-----BEGIN PGP PRIVATE KEY BLOCK-----", "private_key"),
        ("aws_access_key_id = " + "AKIA" + "ABCDEFGHIJKLMNOP", "cloud_access_key"),
        ('{"root_token": "s.abc", "unseal_keys_b64": []}', "vault_keys"),
        ('{"recovery_keys_b64": ["x"]}', "vault_keys"),
        ("Write down your recovery phrase and keep it safe", "recovery_phrase"),
        ("user: admin\npassword: hunter22\n", "credential_value"),
        ("Admin password: hunter22", "credential_value"),
        ("Mon mot de passe : abcd1234", "credential_value"),
        ("Mot de\xa0passe : abcd1234", "credential_value"),
        ("Initial Root Token: s.abcdefgh", "credential_value"),
        ('  "db_password": "abcd1234",', "credential_value"),
        ("Mots de passe : abcd1234", "credential_value"),
        ("mdp: abcd1234", "credential_value"),
        ("Identifiants : abcd1234", "credential_value"),
        ("SECRET_KEY = 'abcd1234efgh'", "credential_value"),
        ("AWS_SECRET_ACCESS_KEY=abcd1234", "credential_value"),
    ],
)
def test_secret_content_is_flagged(text, reason):
    assert secret_reason("notes.txt", text) == reason


@pytest.mark.parametrize(
    "text",
    [
        SWITCH_POLICY,
        "Chapter 3: Backup and Recovery: restore",
        "password: abc",
        "Mot de passe oublié ? Cliquez ici",
    ],
)
def test_settings_without_values_pass(text):
    assert secret_reason("switch-config.txt", text) is None


def test_long_blank_text_is_not_flagged():
    assert secret_reason("notes.txt", "\n" * 50_000) is None
