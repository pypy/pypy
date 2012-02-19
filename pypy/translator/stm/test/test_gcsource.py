from pypy.translator.translator import TranslationContext
from pypy.translator.stm.gcsource import GcSource
from pypy.objspace.flow.model import SpaceOperation, Constant
from pypy.rpython.lltypesystem import lltype


class X:
    def __init__(self, n):
        self.n = n


def gcsource(func, sig):
    t = TranslationContext()
    t.buildannotator().build_types(func, sig)
    t.buildrtyper().specialize()
    gsrc = GcSource(t)
    return gsrc

def test_simple():
    def main(n):
        return X(n)
    gsrc = gcsource(main, [int])
    v_result = gsrc.translator.graphs[0].getreturnvar()
    s = gsrc[v_result]
    assert len(s) == 1
    [op] = list(s)
    assert isinstance(op, SpaceOperation)
    assert op.opname == 'malloc'

def test_two_sources():
    foo = X(42)
    def main(n):
        if n > 5:
            return X(n)
        else:
            return foo
    gsrc = gcsource(main, [int])
    v_result = gsrc.translator.graphs[0].getreturnvar()
    s = gsrc[v_result]
    assert len(s) == 2
    [s1, s2] = list(s)
    if isinstance(s1, SpaceOperation):
        s1, s2 = s2, s1
    assert isinstance(s1, Constant)
    assert s1.value.inst_n == 42
    assert isinstance(s2, SpaceOperation)
    assert s2.opname == 'malloc'

def test_call():
    def f1(n):
        return X(n)
    def main(n):
        return f1(n)
    gsrc = gcsource(main, [int])
    v_result = gsrc.translator.graphs[0].getreturnvar()
    s = gsrc[v_result]
    assert len(s) == 1
    assert list(s)[0].opname == 'malloc'

def test_indirect_call():
    foo = X(42)
    def f1(n):
        return X(n)
    def f2(n):
        return foo
    lst = [f1, f2]
    def main(n):
        return lst[n % 2](n)
    gsrc = gcsource(main, [int])
    v_result = gsrc.translator.graphs[0].getreturnvar()
    s = gsrc[v_result]
    assert len(s) == 2
    [s1, s2] = list(s)
    if isinstance(s1, SpaceOperation):
        s1, s2 = s2, s1
    assert isinstance(s1, Constant)
    assert s1.value.inst_n == 42
    assert isinstance(s2, SpaceOperation)
    assert s2.opname == 'malloc'

def test_argument():
    def f1(x):
        return x
    def main(n):
        return f1(X(5))
    gsrc = gcsource(main, [int])
    v_result = gsrc.translator.graphs[0].getreturnvar()
    s = gsrc[v_result]
    assert len(s) == 1
    assert list(s)[0].opname == 'malloc'

def test_argument_twice():
    foo = X(42)
    def f1(x):
        return x
    def main(n):
        f1(foo)
        return f1(X(5))
    gsrc = gcsource(main, [int])
    v_result = gsrc.translator.graphs[0].getreturnvar()
    s = gsrc[v_result]
    assert len(s) == 2
    [s1, s2] = list(s)
    if isinstance(s1, SpaceOperation):
        s1, s2 = s2, s1
    assert isinstance(s1, Constant)
    assert s1.value.inst_n == 42
    assert isinstance(s2, SpaceOperation)
    assert s2.opname == 'malloc'

def test_unknown_source():
    def main(x):
        return x
    gsrc = gcsource(main, [lltype.Ptr(lltype.GcStruct('S'))])
    v_result = gsrc.translator.graphs[0].getreturnvar()
    s = gsrc[v_result]
    assert list(s) == ['unknown']

def test_exception():
    class FooError(Exception):
        pass
    def f(n):
        raise FooError
    def main(n):
        try:
            f(n)
        except FooError, e:
            return e
    gsrc = gcsource(main, [int])
    v_result = gsrc.translator.graphs[0].getreturnvar()
    s = gsrc[v_result]
    assert list(s) == ['last_exc_value']
