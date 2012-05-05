from pypy.translator.translator import TranslationContext
from pypy.translator.stm.gcsource import GcSource
from pypy.translator.stm.gcsource import TransactionBreakAnalyzer
from pypy.translator.stm.gcsource import break_blocks_after_transaction_breaker
from pypy.objspace.flow.model import SpaceOperation, Constant
from pypy.rpython.lltypesystem import lltype
from pypy.rlib.jit import hint


class X:
    def __init__(self, n):
        self.n = n


def gcsource(func, sig, transactionbreak=False):
    t = TranslationContext()
    t.buildannotator().build_types(func, sig)
    t.buildrtyper().specialize()
    if transactionbreak:
        transactionbreak_analyzer = TransactionBreakAnalyzer(t)
        transactionbreak_analyzer.analyze_all()
        for graph in t.graphs:
            break_blocks_after_transaction_breaker(
                t, graph, transactionbreak_analyzer)
    else:
        transactionbreak_analyzer = None
    gsrc = GcSource(t, transactionbreak_analyzer)
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

def test_hint_xyz():
    def main(n):
        return hint(X(n), xyz=True)
    gsrc = gcsource(main, [int])
    v_result = gsrc.translator.graphs[0].getreturnvar()
    s = gsrc[v_result]
    assert len(s) == 1
    assert list(s)[0].opname == 'malloc'

def test_hint_stm_write():
    def main(n):
        return hint(X(n), stm_write=True)
    gsrc = gcsource(main, [int])
    v_result = gsrc.translator.graphs[0].getreturnvar()
    s = gsrc[v_result]
    assert len(s) == 1
    assert list(s)[0].opname == 'hint'

def test_transactionbroken():
    def break_transaction():
        pass
    break_transaction._transaction_break_ = True
    #
    def main(n):
        x = X(n)
        break_transaction()
        return x
    gsrc = gcsource(main, [int], transactionbreak=True)
    v_result = gsrc.translator.graphs[0].getreturnvar()
    s = gsrc[v_result]
    assert 'transactionbreak' in s
    #
    def main(n):
        break_transaction()
        x = X(n)
        return x
    gsrc = gcsource(main, [int], transactionbreak=True)
    v_result = gsrc.translator.graphs[0].getreturnvar()
    s = gsrc[v_result]
    assert 'transactionbreak' not in s
    #
    def main(n):
        x = X(n)
        break_transaction()
        y = X(n)   # extra operation in the same block
        return x
    gsrc = gcsource(main, [int], transactionbreak=True)
    v_result = gsrc.translator.graphs[0].getreturnvar()
    s = gsrc[v_result]
    assert 'transactionbreak' in s
    #
    def g(n):
        break_transaction()
        return X(n)
    def main(n):
        return g(n)
    gsrc = gcsource(main, [int], transactionbreak=True)
    v_result = gsrc.translator.graphs[0].getreturnvar()
    s = gsrc[v_result]
    assert 'transactionbreak' not in s
