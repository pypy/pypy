# those tests only work after transation with the new _structseq changes, since
# _structseq is frozen in
import pytest

import sys
from _structseq import structseqtype, structseqfield

class foo:
    __metaclass__ = structseqtype
    f1 = structseqfield(0, "a")
    f2 = structseqfield(1, "b")
    f3 = structseqfield(2, "c")

    f5 = structseqfield(4, "nonconsecutive")
    f6 = structseqfield(5, "nonconsecutive2", default=lambda self: -15)

def test_structseqtype():
    t = foo((1, 2, 3))
    assert isinstance(t, tuple)
    assert t.f1 == 1
    assert t.f2 == 2
    assert t.f3 == 3
    assert t.f5 is None

    t = foo((1, 2, 3, 4))
    assert t.f1 == 1
    assert t.f2 == 2
    assert t.f3 == 3
    assert t.f5 == 4
    assert t.f6 == -15
    assert tuple(t) == (1, 2, 3) # only positional

    t = foo((1, 2, 3), dict(f5=4))
    assert t.f1 == 1
    assert t.f2 == 2
    assert t.f3 == 3
    assert t.f5 == 4
    assert t.f6 == -15
    assert tuple(t) == (1, 2, 3) # only positional

    t = foo((1, 2, 3, 4, 5))
    assert t.f1 == 1
    assert t.f2 == 2
    assert t.f3 == 3
    assert t.f5 == 4
    assert t.f6 == 5
    assert tuple(t) == (1, 2, 3)

    t = foo((1, 2, 3), dict(f5=4, f6=12))
    assert t.f1 == 1
    assert t.f2 == 2
    assert t.f3 == 3
    assert t.f5 == 4
    assert t.f6 == 12
    assert tuple(t) == (1, 2, 3)

    t = foo((1, 2, 3, 4), dict(f6=12))
    assert t.f1 == 1
    assert t.f2 == 2
    assert t.f3 == 3
    assert t.f5 == 4
    assert t.f6 == 12
    assert tuple(t) == (1, 2, 3)

    with pytest.raises(TypeError):
        foo((1, ))
    with pytest.raises(TypeError):
        foo((1, ) * 6)
    with pytest.raises(TypeError):
        foo((1, 2, 3, 4), dict(f5=5))


def test_dict_extra_keys_ignored():
    t = foo((1, 2, 3), dict(a=2))
    assert not hasattr(t, 'a') # follow CPython

def test_dict_mapdict():
    import __pypy__
    t = foo((1, 2, 3, 4), dict(f6=12))
    assert __pypy__.strategy(t.__dict__) == 'MapDictStrategy'

def test_dict_structseqfield_immutable():
    import __pypy__
    assert __pypy__.strategy(foo.f5).count("immutable") == 5

def test_default_only_nonpositional():
    with pytest.raises(AssertionError):
        class foo:
            __metaclass__ = structseqtype
            f1 = structseqfield(0, "a", default=lambda self: 0)


def test_trace_get():
    l = []
    def trace(frame, event, *args):
        l.append((frame, event, ) + args)
        return trace

    t = foo((1, 2, 3))
    sys.settrace(trace)
    assert t.f1 == 1
    sys.settrace(None)
    assert l == []
