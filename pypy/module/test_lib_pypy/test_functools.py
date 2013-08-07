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
