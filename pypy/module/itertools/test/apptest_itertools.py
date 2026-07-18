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

def test_batched():
    from itertools import batched
    assert list(batched('ABCDEFG', 3)) == [
        ('A', 'B', 'C'), ('D', 'E', 'F'), ('G',)]
    assert list(batched('ABCDEF', 3)) == [('A', 'B', 'C'), ('D', 'E', 'F')]
    assert list(batched('', 3)) == []
    # n as keyword
    assert list(batched('ABCD', n=2)) == [('A', 'B'), ('C', 'D')]
    # n must be at least one
    with pytest.raises(ValueError):
        list(batched('ABC', 0))
    with pytest.raises(ValueError):
        list(batched('ABC', -1))
    # exhausted iterator stays exhausted
    it = batched('AB', 5)
    assert next(it) == ('A', 'B')
    with pytest.raises(StopIteration):
        next(it)
    with pytest.raises(StopIteration):
        next(it)

def test_tee_of_tee_independent():
    # gh-123884 / pypy #5284: tee() of a tee'd iterator must produce
    # independent iterators sharing the buffer, not the input itself.
    from itertools import tee
    def consume(it, up_to):
        i = 0
        while i < up_to:
            try:
                next(it)
            except StopIteration:
                break
            i += 1
        return i
    [my_iter] = tee(iter(range(100)), 1)
    [preview] = tee(my_iter, 1)
    assert preview is not my_iter
    assert consume(preview, 5) == 5
    assert consume(my_iter, 100) == 100
