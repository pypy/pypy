import pytest

from itertools import pairwise

def test_pairwise():
    assert list(pairwise([])) == []
    assert list(pairwise([1])) == []
    assert list(pairwise([1, 2])) == [(1, 2)]
    assert list(pairwise([1, 2, 3])) == [(1, 2), (2, 3)]

def test_posonly():
    with pytest.raises(TypeError):
        pairwise(iterable='abc')
