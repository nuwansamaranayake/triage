from app.engine.clustering import ItemForClustering, build_clusters
from app.engine.embedding import HashingEmbedder


def _items():
    return [
        ItemForClustering(item_id=1, text="crashes on login after update",
                          aspect_keys=["crash_login"]),
        ItemForClustering(item_id=2, text="login crash again, lost my session",
                          aspect_keys=["crash_login"]),
        ItemForClustering(item_id=3, text="sync is painfully slow since v2",
                          aspect_keys=["slow_sync"]),
        ItemForClustering(item_id=4, text="slow sync and it crashed at login too",
                          aspect_keys=["slow_sync", "crash_login"]),
    ]


def test_seeded_clusters_from_aspect_keys():
    result = build_clusters(_items(), HashingEmbedder())
    assert sorted(result.clusters) == ["crash_login", "slow_sync"]
    crash_ids = [m.item_id for m in result.clusters["crash_login"]]
    assert crash_ids == [1, 2, 4]  # multi-aspect item 4 joins both clusters
    assert [m.item_id for m in result.clusters["slow_sync"]] == [3, 4]
    assert all(m.method == "seeded" and m.similarity == 1.0
               for ms in result.clusters.values() for m in ms)


def test_unlabeled_items_assigned_by_embedding():
    items = _items() + [
        ItemForClustering(item_id=5, text="the login screen crashes constantly"),
    ]
    result = build_clusters(items, HashingEmbedder())
    crash = result.clusters["crash_login"]
    assigned = [m for m in crash if m.item_id == 5]
    assert len(assigned) == 1
    assert assigned[0].method == "embedding"
    assert assigned[0].similarity > 0.15
    assert result.unassigned == []


def test_dissimilar_unlabeled_item_stays_unassigned():
    items = _items() + [
        ItemForClustering(item_id=9, text="zzz qqq xyzzy plugh"),
    ]
    result = build_clusters(items, HashingEmbedder())
    assert result.unassigned == [9]


def test_no_clusters_means_all_unlabeled_unassigned():
    result = build_clusters(
        [ItemForClustering(item_id=1, text="anything at all")], HashingEmbedder())
    assert result.clusters == {}
    assert result.unassigned == [1]


def test_clustering_is_deterministic():
    items = _items() + [
        ItemForClustering(item_id=5, text="the login screen crashes constantly"),
        ItemForClustering(item_id=6, text="sync got really slow"),
    ]
    a = build_clusters(items, HashingEmbedder())
    b = build_clusters(items, HashingEmbedder())
    assert a == b
