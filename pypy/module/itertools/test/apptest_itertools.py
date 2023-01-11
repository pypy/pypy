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

def test_count_complex():
    assert list(islice(count(3.25-4j), 3)) == [3.25-4j, 4.25-4j, 5.25-4j]
