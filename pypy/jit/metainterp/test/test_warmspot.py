from pypy.jit.metainterp.warmspot import ll_meta_interp, cast_whatever_to_int
from pypy.rlib.jit import JitDriver
from pypy.jit.backend.llgraph import runner


def test_translate_cast_whatever_to_int():
    from pypy.rpython.test.test_llinterp import interpret
    from pypy.rpython.lltypesystem import lltype
    def fn(x):
        return cast_whatever_to_int(lltype.typeOf(x), x)
    for type_system in ('lltype', 'ootype'):
        res = interpret(fn, [42], type_system=type_system)
        assert res == 42

class Exit(Exception):
    def __init__(self, result):
        self.result = result


class WarmspotTests(object):
    def meta_interp(self, *args, **kwds):
        assert 'CPUClass' not in kwds
        assert 'type_system' not in kwds
        kwds['CPUClass'] = self.CPUClass
        kwds['type_system'] = self.type_system
        return ll_meta_interp(*args, **kwds)
    
    def test_basic(self):
        mydriver = JitDriver(reds=['a'],
                             greens=['i'])
        CODE_INCREASE = 0
        CODE_JUMP = 1
        lst = [CODE_INCREASE, CODE_INCREASE, CODE_JUMP]
        def interpreter_loop(a):
            i = 0
            while True:
                mydriver.jit_merge_point(i=i, a=a)
                if i >= len(lst):
                    break
                elem = lst[i]
                if elem == CODE_INCREASE:
                    a = a + 1
                    i += 1
                elif elem == CODE_JUMP:
                    if a < 20:
                        i = 0
                        mydriver.can_enter_jit(i=i, a=a)
                    else:
                        i += 1
                else:
                    pass
            raise Exit(a)

        def main(a):
            try:
                interpreter_loop(a)
            except Exit, e:
                return e.result

        res = self.meta_interp(main, [1])
        assert res == 21

    def test_reentry(self):
        mydriver = JitDriver(reds = ['n'], greens = [])

        def f(n):
            while n > 0:
                mydriver.can_enter_jit(n=n)
                mydriver.jit_merge_point(n=n)
                if n % 20 == 0:
                    n -= 2
                n -= 1

        res = self.meta_interp(f, [60])
        assert res == f(30)

    def test_hash_collision(self):
        mydriver = JitDriver(reds = ['n'], greens = ['m'])
        def f(n):
            m = 0
            while n > 0:
                mydriver.can_enter_jit(n=n, m=m)
                mydriver.jit_merge_point(n=n, m=m)
                n -= 1
                if not (n % 11):
                    m = (m+n) & 3
            return m
        res = self.meta_interp(f, [110], hash_bits=1)
        assert res == f(110)


class TestLLWarmspot(WarmspotTests):
    CPUClass = runner.LLtypeCPU
    type_system = 'lltype'

class TestOOWarmspot(WarmspotTests):
    CPUClass = runner.OOtypeCPU
    type_system = 'ootype'
