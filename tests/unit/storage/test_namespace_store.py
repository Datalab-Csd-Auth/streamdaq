import lmdb
import pytest
from pydantic import BaseModel

from streamdaq.storage.codecs import IntCodec, PydanticCodec
from streamdaq.storage.namespace_store import NamespaceStore


class _Point(BaseModel):
    x: int
    y: int


@pytest.fixture
def env(tmp_path):
    environment = lmdb.open(str(tmp_path / "db"), subdir=True, max_dbs=8, map_size=1 << 20)
    yield environment
    environment.close()


class TestNamespaceStoreCodecs:
    def test_pydantic_codec_round_trips_the_model(self, env):
        store = NamespaceStore(env, "points", PydanticCodec(_Point))
        store["a"] = _Point(x=1, y=2)
        assert store["a"] == _Point(x=1, y=2)

    def test_int_codec_round_trips_the_value(self, env):
        store = NamespaceStore(env, "ints", IntCodec())
        store["a"] = 1_000_000
        assert store["a"] == 1_000_000


class TestNamespaceStoreMapping:
    def test_missing_key_getitem_raises_keyerror(self, env):
        store = NamespaceStore(env, "ints", IntCodec())
        with pytest.raises(KeyError):
            store["absent"]

    def test_get_returns_default_for_missing_key(self, env):
        store = NamespaceStore(env, "ints", IntCodec())
        assert store.get("absent") is None
        assert store.get("absent", 7) == 7

    def test_setitem_overwrites(self, env):
        store = NamespaceStore(env, "ints", IntCodec())
        store["a"] = 1
        store["a"] = 2
        assert store["a"] == 2

    def test_contains_reflects_presence(self, env):
        store = NamespaceStore(env, "ints", IntCodec())
        assert "a" not in store
        store["a"] = 1
        assert "a" in store

    def test_delitem_removes_the_key(self, env):
        store = NamespaceStore(env, "ints", IntCodec())
        store["a"] = 1
        del store["a"]
        assert "a" not in store

    def test_delitem_missing_key_raises_keyerror(self, env):
        store = NamespaceStore(env, "ints", IntCodec())
        with pytest.raises(KeyError):
            del store["absent"]

    def test_items_yields_all_pairs(self, env):
        store = NamespaceStore(env, "ints", IntCodec())
        store["a"] = 1
        store["b"] = 2
        assert dict(store.items()) == {"a": 1, "b": 2}

    def test_clear_empties_the_namespace(self, env):
        store = NamespaceStore(env, "ints", IntCodec())
        store["a"] = 1
        store["b"] = 2
        store.clear()
        assert list(store.items()) == []


class TestNamespaceStoreIsolation:
    def test_same_key_in_two_namespaces_does_not_collide(self, env):
        points = NamespaceStore(env, "points", PydanticCodec(_Point))
        counts = NamespaceStore(env, "counts", IntCodec())
        points["shared"] = _Point(x=9, y=9)
        counts["shared"] = 42
        assert points["shared"] == _Point(x=9, y=9)
        assert counts["shared"] == 42

    def test_clear_is_scoped_to_one_namespace(self, env):
        points = NamespaceStore(env, "points", PydanticCodec(_Point))
        counts = NamespaceStore(env, "counts", IntCodec())
        points["p"] = _Point(x=1, y=1)
        counts["c"] = 1
        points.clear()
        assert "p" not in points
        assert counts["c"] == 1  # the other namespace is untouched

    def test_reopening_the_namespace_sees_persisted_values(self, env):
        NamespaceStore(env, "ints", IntCodec())["a"] = 5
        reopened = NamespaceStore(env, "ints", IntCodec())
        assert reopened["a"] == 5
