import pytest


def test_new():
    def cmp_slice(sl1, sl2):
        for attr in "start", "stop", "step":
            if getattr(sl1, attr) != getattr(sl2, attr):
                return False
        return True
    pytest.raises(TypeError, slice)
    pytest.raises(TypeError, slice, 1, 2, 3, 4)
    assert cmp_slice(slice(23), slice(None, 23, None))
    assert cmp_slice(slice(23, 45), slice(23, 45, None))

def test_indices():
    assert slice(4,11,2).indices(28) == (4, 11, 2)
    assert slice(4,11,2).indices(8) == (4, 8, 2)
    assert slice(4,11,2).indices(2) == (2, 2, 2)
    assert slice(11,4,-2).indices(28) == (11, 4, -2)
    assert slice(11,4,-2).indices(8) == (7, 4, -2)
    assert slice(11,4,-2).indices(2) == (1, 1, -2)
    assert slice(None, -9).indices(10) == (0, 1, 1)
    assert slice(None, -10, -1).indices(10) == (9, 0, -1)
    assert slice(None, 10, -1).indices(10) == (9, 9, -1)

def test_repr():
    assert repr(slice(1, 2, 3)) == 'slice(1, 2, 3)'
    assert repr(slice(1, 2)) == 'slice(1, 2, None)'
    assert repr(slice('a', 'b')) == "slice('a', 'b', None)"

def test_eq():
    slice1 = slice(1, 2, 3)
    slice2 = slice(1, 2, 3)
    assert slice1 == slice2
    assert not slice1 != slice2
    slice2 = slice(1, 2)
    assert slice1 != slice2

def test_hash():
    # slices are hashable since 3.12
    assert slice.__hash__ is not None
    s = slice(1, 5)
    assert {s} == {slice(1, 5)}
    d = {slice(1, 2, 3): 'x'}
    assert d[slice(1, 2, 3)] == 'x'
    # equal slices hash equal; slice(a, b) == slice(a, b, None)
    assert hash(slice(1, 5)) == hash(slice(1, 5, None))
    assert hash(slice(1, 2, 3)) != hash(slice(3, 2, 1))
    import sys
    if sys.maxsize == 2 ** 63 - 1:
        # All-integer slices match CPython 3.12 exactly on 64-bit. (Slices
        # containing None do not, because PyPy's hash(None) differs from
        # CPython's fixed value -- a separate gap, unrelated to slice hashing.)
        assert hash(slice(1, 2, 3)) == -2340833382717974474
    # an unhashable component makes the slice unhashable
    with pytest.raises(TypeError):
        hash(slice(1, [], 3))

def test_lt():
    assert slice(0, 2, 3) < slice(1, 0, 0)
    assert slice(0, 1, 3) < slice(0, 2, 0)
    assert slice(0, 1, 2) < slice(0, 1, 3)
    assert not (slice(1, 2, 3) < slice(0, 0, 0))
    assert not (slice(1, 2, 3) < slice(1, 0, 0))
    assert not (slice(1, 2, 3) < slice(1, 2, 0))
    assert not (slice(1, 2, 3) < slice(1, 2, 3))

def test_long_indices():
    assert slice(-2 ** 100, 10, 1).indices(1000) == (0, 10, 1)
    assert slice(-2 ** 200, -2 ** 100, 1).indices(1000) == (0, 0, 1)
    assert slice(2 ** 100, 0, -1).indices(1000) == (999, 0, -1)
    assert slice(2 ** 100, -2 ** 100, -1).indices(1000) == (999, -1, -1)
    assert slice(0, 1000, 2 ** 200).indices(1000) == (0, 1000, 2 ** 200)
    assert slice(0, 1000, 1).indices(2 ** 100) == (0, 1000, 1)

def test_reduce():
    assert slice(1, 2, 3).__reduce__() == (slice, (1, 2, 3))

def test_indices_negative_length():
    with pytest.raises(ValueError):
        slice(0, 1000, 1).indices(-1)
