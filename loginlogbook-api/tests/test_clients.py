"""Tests for the client store."""
from pathlib import Path

import pytest

from app.client_store import ClientStore


def test_tokens_empty_when_file_missing(tmp_path: Path):
    store = ClientStore(tmp_path / "clients.json")
    assert store.tokens() == []


def test_list_names_empty_when_file_missing(tmp_path: Path):
    store = ClientStore(tmp_path / "clients.json")
    assert store.list_names() == []


def test_add_and_list(tmp_path: Path):
    store = ClientStore(tmp_path / "clients.json")
    store.add("ws-01", "token-a")
    assert store.list_names() == ["ws-01"]
    assert store.tokens() == ["token-a"]


def test_add_duplicate_name_raises(tmp_path: Path):
    store = ClientStore(tmp_path / "clients.json")
    store.add("ws-01", "token-a")
    with pytest.raises(ValueError, match="ws-01"):
        store.add("ws-01", "token-b")


def test_remove_existing_returns_true(tmp_path: Path):
    store = ClientStore(tmp_path / "clients.json")
    store.add("ws-01", "token-a")
    assert store.remove("ws-01") is True
    assert store.list_names() == []


def test_remove_unknown_returns_false(tmp_path: Path):
    store = ClientStore(tmp_path / "clients.json")
    assert store.remove("does-not-exist") is False


def test_persists_across_instances(tmp_path: Path):
    path = tmp_path / "clients.json"
    ClientStore(path).add("ws-01", "token-a")
    assert ClientStore(path).list_names() == ["ws-01"]
