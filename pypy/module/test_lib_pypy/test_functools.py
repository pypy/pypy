import pytest

from lib_pypy import _functools


def test_partial_reduce():
    partial = _functools.partial(test_partial_reduce)
    state = partial.__reduce__()
    assert state == (type(partial), (test_partial_reduce,),
                     (test_partial_reduce, (), None, None))

def test_partial_setstate():
    partial = _functools.partial(object)
    partial.__setstate__([test_partial_setstate, (), None, None])
    assert partial.func == test_partial_setstate

def test_partial_pickle():
    import pickle
    partial1 = _functools.partial(test_partial_pickle)
    string = pickle.dumps(partial1)
    partial2 = pickle.loads(string)
    assert partial1.func == partial2.func

def test_immutable_attributes():
    partial = _functools.partial(object)
    with pytest.raises((TypeError, AttributeError)):
        partial.func = sum
    with pytest.raises(TypeError) as exc:
        del partial.__dict__
    assert str(exc.value) == "a partial object's dictionary may not be deleted"
    with pytest.raises(AttributeError):
        del partial.zzz
