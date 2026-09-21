from types import SimpleNamespace

from backend.lim.vector_memory import VectorMemory


def test_stats_uses_qdrant_points_count(monkeypatch):
    memory = VectorMemory()

    info = SimpleNamespace(
        points_count=7,
        status="green",
    )

    fake_client = SimpleNamespace(
        get_collection=lambda collection: info,
    )

    monkeypatch.setattr(memory, "_get_client", lambda: fake_client)

    result = memory.stats("fwg_content")

    assert result == {
        "collection": "fwg_content",
        "vectors_count": 7,
        "status": "green",
    }
