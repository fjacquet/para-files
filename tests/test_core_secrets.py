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
    ],
)
def test_ordinary_names_pass(name):
    assert secret_reason(name, "Invoice total CHF 49.90") is None


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("-----BEGIN OPENSSH PRIVATE KEY-----\nabc", "private_key"),
        ("aws_access_key_id = AKIAABCDEFGHIJKLMNOP", "cloud_access_key"),
        ('{"root_token": "s.abc", "unseal_keys_b64": []}', "vault_keys"),
        ("Write down your recovery phrase and keep it safe", "recovery_phrase"),
        ("user: admin\npassword: hunter22\n", "credential_value"),
    ],
)
def test_secret_content_is_flagged(text, reason):
    assert secret_reason("notes.txt", text) == reason


@pytest.mark.parametrize("text", [SWITCH_POLICY, "Chapter 3: Backup and Recovery: restore"])
def test_settings_without_values_pass(text):
    assert secret_reason("switch-config.txt", text) is None
