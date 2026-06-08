import pytest

from itertools import pairwise, count, islice

def test_pairwise():
    assert list(pairwise([])) == []
    assert list(pairwise([1])) == []
    assert list(pairwise([1, 2])) == [(1, 2)]
    assert list(pairwise([1, 2, 3])) == [(1, 2), (2, 3)]

def test_posonly():
    with pytest.raises(TypeError):
        pairwise(iterable='abc')

def test_pairwise_reenter():
    def check(reenter_at, expected):
        class I:
            count = 0
            def __iter__(self):
                return self
            def __next__(self):
                self.count += 1
                if self.count in reenter_at:
                    return next(it)
                return [self.count]  # new object

        it = pairwise(I())
        for item in expected:
            assert next(it) == item

    check({1}, [
        (([2], [3]), [4]),
        ([4], [5]),
    ])
    check({2}, [
        ([1], ([1], [3])),
        (([1], [3]), [4]),
        ([4], [5]),
    ])
    check({3}, [
        ([1], [2]),
        ([2], ([2], [4])),
        (([2], [4]), [5]),
        ([5], [6]),
    ])
    check({1, 2}, [
        ((([3], [4]), [5]), [6]),
        ([6], [7]),
    ])
    check({1, 3}, [
        (([2], ([2], [4])), [5]),
        ([5], [6]),
    ])
    check({1, 4}, [
        (([2], [3]), (([2], [3]), [5])),
        ((([2], [3]), [5]), [6]),
        ([6], [7]),
    ])
    check({2, 3}, [
        ([1], ([1], ([1], [4]))),
        (([1], ([1], [4])), [5]),
        ([5], [6]),
    ])

def test_count_complex():
    assert list(islice(count(3.25-4j), 3)) == [3.25-4j, 4.25-4j, 5.25-4j]
