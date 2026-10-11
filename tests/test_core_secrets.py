"""Tests for the secrets guard (spec §4.3, S8)."""

from __future__ import annotations

import time

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
        ".env.local.bak",
        "id_rsa_backup.txt",
        "Identifiants.txt",
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
        "Quarterly review.key",
        "id_rsa.pub",
        "Identifiants TVA.pdf",
        "Identifiants fiscaux 2024.pdf",
    ],
)
def test_ordinary_names_pass(name):
    assert secret_reason(name, "Invoice total CHF 49.90") is None


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("-----BEGIN " + "OPENSSH PRIVATE KEY-----\nabc", "private_key"),
        ("-----BEGIN " + "PGP PRIVATE KEY BLOCK-----", "private_key"),
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
        ("CLIENT_SECRET_FOR_PRODUCTION_ENVIRONMENT=abcd1234", "credential_value"),
        (
            "CLIENT_SECRET_FOR_PRODUCTION_ENVIRONMENT_EU_WEST_RELEASE_KEY=abcd1234",
            "credential_value",
        ),
        ("password:\n  hunter22", "credential_value"),
        ("Password:\nabcd1234", "credential_value"),
        ("Password:\r\nabcd1234", "credential_value"),
        ("password: https://user:pass@host", "credential_value"),
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
        "Password:\n\nDear customer, your account is ready",
        "Password:\nDear customer here",
        "Reset your password: https://example.com/reset",
        "password\n: abcd1234",
        "mdpfoo: abcd1234",
        "identifiantsX: abcd1234",
    ],
)
def test_settings_without_values_pass(text):
    assert secret_reason("switch-config.txt", text) is None


def test_long_blank_text_is_not_flagged():
    assert secret_reason("notes.txt", "\n" * 50_000) is None


def test_long_marker_run_is_not_flagged():
    text = "password" * 8000
    started = time.perf_counter()
    assert secret_reason("notes.txt", text) is None
    assert time.perf_counter() - started < 1.0


def test_private_key_header_is_flagged_whatever_the_name():
    text = "-----BEGIN " + "RSA PRIVATE KEY-----\nabc"
    assert secret_reason("Quarterly review.key", text) == "private_key"
