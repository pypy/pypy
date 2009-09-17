"""
This is a test that translates a complete JIT to C and runs it.  It is
not testing much, expect that it basically works.  What it *is* testing,
however, is the correct handling of GC, i.e. if objects are freed as
soon as possible (at least in a simple case).
"""
import weakref, random
import py
from pypy.rlib import rgc
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.jit import JitDriver, OPTIMIZER_SIMPLE
from pypy.jit.backend.x86.runner import CPU386
from pypy.jit.backend.llsupport.gc import GcRefList, GcRootMap_asmgcc
from pypy.jit.backend.x86.regalloc import stack_pos


class X(object):
    next = None

class CheckError(Exception):
    pass

def check(flag):
    if not flag:
        raise CheckError


def get_test(main):
    main._dont_inline_ = True

    def g(n):
        x = X()
        x.foo = 2
        main(n, x)
        x.foo = 5
        return weakref.ref(x)
    g._dont_inline_ = True

    def entrypoint(args):
        r_list = []
        for i in range(20):
            r = g(2000)
            r_list.append(r)
            rgc.collect()
        rgc.collect(); rgc.collect()
        freed = 0
        for r in r_list:
            if r() is None:
                freed += 1
        print freed
        return 0

    return entrypoint


def compile_and_run(f, gc, CPUClass=CPU386, **kwds):
    from pypy.annotation.listdef import s_list_of_strings
    from pypy.translator.translator import TranslationContext
    from pypy.jit.metainterp.warmspot import apply_jit
    from pypy.translator.c import genc
    #
    t = TranslationContext()
    t.config.translation.gc = gc
    t.config.translation.gcconfig.debugprint = True
    for name, value in kwds.items():
        setattr(t.config.translation, name, value)
    t.buildannotator().build_types(f, [s_list_of_strings])
    t.buildrtyper().specialize()
    if kwds['jit']:
        apply_jit(t, CPUClass=CPUClass, optimizer=OPTIMIZER_SIMPLE)
    cbuilder = genc.CStandaloneBuilder(t, f, t.config)
    cbuilder.generate_source()
    cbuilder.compile()
    #
    data = cbuilder.cmdexec('')
    return data.strip()


def test_compile_boehm():
    myjitdriver = JitDriver(greens = [], reds = ['n', 'x'])
    def main(n, x):
        while n > 0:
            myjitdriver.can_enter_jit(n=n, x=x)
            myjitdriver.jit_merge_point(n=n, x=x)
            y = X()
            y.foo = x.foo
            n -= y.foo
    res = compile_and_run(get_test(main), "boehm", jit=True)
    assert int(res) >= 16

def test_compile_hybrid_1():
    # a moving GC.  Supports malloc_varsize_nonmovable.  Simple test, works
    # without write_barriers and root stack enumeration.
    myjitdriver = JitDriver(greens = [], reds = ['n', 'x'])
    def main(n, x):
        while n > 0:
            myjitdriver.can_enter_jit(n=n, x=x)
            myjitdriver.jit_merge_point(n=n, x=x)
            y = X()
            y.foo = x.foo
            n -= y.foo
    res = compile_and_run(get_test(main), "hybrid", gcrootfinder="asmgcc",
                          jit=True)
    assert int(res) == 20

def test_compile_hybrid_2():
    # More complex test, requires root stack enumeration but
    # not write_barriers.
    myjitdriver = JitDriver(greens = [], reds = ['n', 'x'])
    def main(n, x):
        while n > 0:
            myjitdriver.can_enter_jit(n=n, x=x)
            myjitdriver.jit_merge_point(n=n, x=x)
            prev = x
            for j in range(101):    # main() runs 20'000 times, thus allocates
                y = X()             # a total of 2'020'000 objects
                y.foo = prev.foo
                prev = y
            n -= prev.foo
    res = compile_and_run(get_test(main), "hybrid", gcrootfinder="asmgcc",
                          jit=True)
    assert int(res) == 20

def test_compile_hybrid_3():
    # Third version of the test.  Really requires write_barriers.
    myjitdriver = JitDriver(greens = [], reds = ['n', 'x'])
    def main(n, x):
        while n > 0:
            myjitdriver.can_enter_jit(n=n, x=x)
            myjitdriver.jit_merge_point(n=n, x=x)
            x.next = None
            for j in range(101):    # main() runs 20'000 times, thus allocates
                y = X()             # a total of 2'020'000 objects
                y.foo = j+1
                y.next = x.next
                x.next = y
            check(x.next.foo == 101)
            total = 0
            y = x
            for j in range(101):
                y = y.next
                total += y.foo
            check(not y.next)
            check(total == 101*102/2)
            n -= x.foo
    x_test = X()
    x_test.foo = 5
    main(6, x_test)     # check that it does not raise CheckError
    res = compile_and_run(get_test(main), "hybrid", gcrootfinder="asmgcc",
                          jit=True)
    assert int(res) == 20

def test_compile_hybrid_3_extra():
    # Extra version of the test, with tons of live vars around the residual
    # call that all contain a GC pointer.
    myjitdriver = JitDriver(greens = [], reds = ['n', 'x0', 'x1', 'x2', 'x3',
                                                      'x4', 'x5', 'x6', 'x7'])
    def residual(n=26):
        x = X()
        x.next = X()
        x.next.foo = n
        return x
    residual._look_inside_me_ = False
    #
    def main(n, x):
        residual(5)
        x0 = residual()
        x1 = residual()
        x2 = residual()
        x3 = residual()
        x4 = residual()
        x5 = residual()
        x6 = residual()
        x7 = residual()
        n *= 19
        while n > 0:
            myjitdriver.can_enter_jit(n=n, x0=x0, x1=x1, x2=x2, x3=x3,
                                           x4=x4, x5=x5, x6=x6, x7=x7)
            myjitdriver.jit_merge_point(n=n, x0=x0, x1=x1, x2=x2, x3=x3,
                                             x4=x4, x5=x5, x6=x6, x7=x7)
            x8 = residual()
            x9 = residual()
            check(x0.next.foo == 26)
            check(x1.next.foo == 26)
            check(x2.next.foo == 26)
            check(x3.next.foo == 26)
            check(x4.next.foo == 26)
            check(x5.next.foo == 26)
            check(x6.next.foo == 26)
            check(x7.next.foo == 26)
            check(x8.next.foo == 26)
            check(x9.next.foo == 26)
            x0, x1, x2, x3, x4, x5, x6, x7 = x7, x4, x6, x5, x3, x2, x9, x8
            n -= 1
    main(6, None)     # check that it does not raise AssertionError
    res = compile_and_run(get_test(main), "hybrid", gcrootfinder="asmgcc",
                          jit=True)
    assert int(res) == 20

def test_compile_hybrid_4():
    # Fourth version of the test, with __del__.
    from pypy.rlib.debug import debug_print
    class Counter:
        cnt = 0
    counter = Counter()
    class Z:
        def __del__(self):
            counter.cnt -= 1
    myjitdriver = JitDriver(greens = [], reds = ['n', 'x'])
    def main(n, x):
        debug_print('counter.cnt =', counter.cnt)
        check(counter.cnt < 5)
        counter.cnt = n // x.foo
        while n > 0:
            myjitdriver.can_enter_jit(n=n, x=x)
            myjitdriver.jit_merge_point(n=n, x=x)
            Z()
            n -= x.foo
    res = compile_and_run(get_test(main), "hybrid", gcrootfinder="asmgcc",
                          jit=True)
    assert int(res) == 20

def test_compile_hybrid_5():
    # Test string manipulation.
    myjitdriver = JitDriver(greens = [], reds = ['n', 'x', 's'])
    def main(n, x):
        s = ''
        while n > 0:
            myjitdriver.can_enter_jit(n=n, x=x, s=s)
            myjitdriver.jit_merge_point(n=n, x=x, s=s)
            n -= x.foo
            s += str(n)
        check(len(s) == 1*5 + 2*45 + 3*450 + 4*500)
    res = compile_and_run(get_test(main), "hybrid", gcrootfinder="asmgcc",
                          jit=True)
    assert int(res) == 20

def test_compile_hybrid_6():
    # Array manipulation (i.e. fixed-sized list).
    myjitdriver = JitDriver(greens = [], reds = ['n', 'x', 'l'])
    def main(n, x):
        l = []
        while n > 0:
            myjitdriver.can_enter_jit(n=n, x=x, l=l)
            myjitdriver.jit_merge_point(n=n, x=x, l=l)
            if n < 200:
                l = [n, n, n]
            if n < 100:
                check(len(l) == 3)
                check(l[0] == n)
                check(l[1] == n)
                check(l[2] == n)
            n -= x.foo
        check(len(l) == 3)
        check(l[0] == 2)
        check(l[1] == 2)
        check(l[2] == 2)
    res = compile_and_run(get_test(main), "hybrid", gcrootfinder="asmgcc",
                          jit=True)
    assert int(res) == 20

def test_compile_hybrid_7():
    # Array of pointers (test the write barrier for setarrayitem_gc)
    class X:
        def __init__(self, x):
            self.x = x
    myjitdriver = JitDriver(greens = [], reds = ['n', 'x', 'l'])
    def main(n, x):
        l = [X(123)]
        while n > 0:
            myjitdriver.can_enter_jit(n=n, x=x, l=l)
            myjitdriver.jit_merge_point(n=n, x=x, l=l)
            if n < 1900:
                check(l[0].x == 123)
                l = [None] * 16
                l[0] = X(123)
                l[1] = X(n)
                l[2] = X(n+10)
                l[3] = X(n+20)
                l[4] = X(n+30)
                l[5] = X(n+40)
                l[6] = X(n+50)
                l[7] = X(n+60)
                l[8] = X(n+70)
                l[9] = X(n+80)
                l[10] = X(n+90)
                l[11] = X(n+100)
                l[12] = X(n+110)
                l[13] = X(n+120)
                l[14] = X(n+130)
                l[15] = X(n+140)
            if n < 1800:
                check(len(l) == 16)
                check(l[0].x == 123)
                check(l[1].x == n)
                check(l[2].x == n+10)
                check(l[3].x == n+20)
                check(l[4].x == n+30)
                check(l[5].x == n+40)
                check(l[6].x == n+50)
                check(l[7].x == n+60)
                check(l[8].x == n+70)
                check(l[9].x == n+80)
                check(l[10].x == n+90)
                check(l[11].x == n+100)
                check(l[12].x == n+110)
                check(l[13].x == n+120)
                check(l[14].x == n+130)
                check(l[15].x == n+140)
            n -= x.foo
        check(len(l) == 16)
        check(l[0].x == 123)
        check(l[1].x == 2)
        check(l[2].x == 12)
        check(l[3].x == 22)
        check(l[4].x == 32)
        check(l[5].x == 42)
        check(l[6].x == 52)
        check(l[7].x == 62)
        check(l[8].x == 72)
        check(l[9].x == 82)
        check(l[10].x == 92)
        check(l[11].x == 102)
        check(l[12].x == 112)
        check(l[13].x == 122)
        check(l[14].x == 132)
        check(l[15].x == 142)

    class CPU386CollectOnLeave(CPU386):

        def execute_operations(self, loop, verbose=False):
            op = CPU386.execute_operations(self, loop, verbose)
            rgc.collect(0)
            return op            
        
    res = compile_and_run(get_test(main), "hybrid", gcrootfinder="asmgcc",
                          CPUClass=CPU386CollectOnLeave, jit=True)
    assert int(res) == 20
