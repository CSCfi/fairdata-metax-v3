from apps.common.helpers import merge_sets


def test_merge_sets():
    joined = merge_sets(
        [
            [1, 2, 3],
            [3, 4],
            [5, 3],
            [6],
            [7, 8],
            [7, 9],
            [10, 6],
            [11],
            [2, 12],
        ]
    )
    joined = sorted(sorted(v) for v in joined)
    assert joined == [[1, 2, 3, 4, 5, 12], [6, 10], [7, 8, 9], [11]]


def test_merge_sets_2():
    joined = merge_sets([[1, 2], [3, 4], [2, 3]])
    joined = sorted(sorted(v) for v in joined)
    assert joined == [[1, 2, 3, 4]]


def test_merge_sets_3():
    joined = merge_sets(
        [
            [8, 100],
            [120, 8],
            [0],
            [1, 2],
            [9, 8],
            [2, 3],
            [8, 7],
            [3, 4],
            [7, 6],
            [4, 5],
            [6, 5],
            [10, 1],
            [2, 7],
            [15, 14, 8, 12],
        ]
    )
    joined = sorted(sorted(v) for v in joined)
    assert joined == [[0], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 15, 100, 120]]
