"""SQLite cache: ISBN lookups and verdicts; fingerprint of the config files and model."""

from __future__ import annotations

import threading

from para_files.core.cache import Cache, config_fingerprint


def test_roundtrip_and_miss(tmp_path):
    cache = Cache(tmp_path / "c" / "cache.sqlite")
    assert cache.get_isbn("123") is None
    cache.put_isbn("123", {"title": "T"})
    assert cache.get_isbn("123") == {"title": "T"}
    assert cache.get_verdict("sha", "fp") is None
    cache.put_verdict("sha", "fp", {"leaf_id": "x"})
    assert cache.get_verdict("sha", "fp") == {"leaf_id": "x"}
    assert cache.get_verdict("sha", "other") is None
    cache.close()


def test_persists_across_instances(tmp_path):
    path = tmp_path / "cache.sqlite"
    first = Cache(path)
    first.put_verdict("sha", "fp", {"leaf_id": "x"})
    first.close()
    second = Cache(path)
    assert second.get_verdict("sha", "fp") == {"leaf_id": "x"}
    second.close()


def test_threads_share_one_cache(tmp_path):
    cache = Cache(tmp_path / "cache.sqlite")

    def work(n):
        for i in range(50):
            cache.put_isbn(f"{n}-{i}", {"i": i})
            assert cache.get_isbn(f"{n}-{i}") == {"i": i}

    threads = [threading.Thread(target=work, args=(n,)) for n in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert cache.get_isbn("3-49") == {"i": 49}
    cache.close()


def test_fingerprint_follows_files_and_model(tmp_path):
    (tmp_path / "tree.yaml").write_text("leaves: {}\n")
    base = config_fingerprint(tmp_path, "model-a")
    assert config_fingerprint(tmp_path, "model-a") == base
    assert config_fingerprint(tmp_path, "model-b") != base
    (tmp_path / "rules.yaml").write_text("rules: []\n")
    assert config_fingerprint(tmp_path, "model-a") != base
