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
from pypy.rlib.jit import JitDriver
from pypy.jit.backend.x86.runner import CPU386
from pypy.jit.backend.x86.gc import GcRefList, GcRootMap_asmgcc
from pypy.jit.backend.x86.regalloc import stack_pos


class X(object):
    next = None

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


def compile_and_run(f, gc, **kwds):
    from pypy.annotation.listdef import s_list_of_strings
    from pypy.translator.translator import TranslationContext
    from pypy.jit.metainterp.warmspot import apply_jit
    from pypy.jit.metainterp import simple_optimize
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
        apply_jit(t, CPUClass=CPU386, optimizer=simple_optimize)
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

def test_GcRefList():
    S = lltype.GcStruct('S')
    order = range(20000) * 4
    random.shuffle(order)
    def fn(args):
        allocs = [lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(S))
                  for i in range(20000)]
        allocs = [allocs[i] for i in order]
        #
        gcrefs = GcRefList()
        addrs = [gcrefs.get_address_of_gcref(ptr) for ptr in allocs]
        for i in range(len(allocs)):
            assert addrs[i].address[0] == llmemory.cast_ptr_to_adr(allocs[i])
        return 0
    compile_and_run(fn, "hybrid", gcrootfinder="asmgcc", jit=False)

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

def test_GcRootMap_asmgcc():
    gcrootmap = GcRootMap_asmgcc()
    shape = gcrootmap._get_callshape([stack_pos(1), stack_pos(55)])
    num1 = stack_pos(1).ofs_relative_to_ebp()
    num2 = stack_pos(55).ofs_relative_to_ebp()
    assert shape == [6, -2, -6, -10, 2, 0, num1|2, num2|2]
    #
    shapeaddr = gcrootmap.encode_callshape([stack_pos(1), stack_pos(55)])
    PCALLSHAPE = lltype.Ptr(GcRootMap_asmgcc.CALLSHAPE_ARRAY)
    p = llmemory.cast_adr_to_ptr(shapeaddr, PCALLSHAPE)
    num1a = -2*(num1|2)-1
    num2a = ((-2*(num2|2)-1) >> 7) | 128
    num2b = (-2*(num2|2)-1) & 127
    for i, expected in enumerate([num2a, num2b, num1a, 0, 4, 19, 11, 3, 12]):
        assert p[i] == expected
    #
    retaddr = rffi.cast(llmemory.Address, 1234567890)
    gcrootmap.put(retaddr, shapeaddr)
    assert gcrootmap._gcmap[0] == retaddr
    assert gcrootmap._gcmap[1] == shapeaddr
    assert gcrootmap.gcmapstart().address[0] == retaddr
    #
    # the same as before, but enough times to trigger a few resizes
    expected_shapeaddr = {}
    for i in range(1, 600):
        shapeaddr = gcrootmap.encode_callshape([stack_pos(i)])
        expected_shapeaddr[i] = shapeaddr
        retaddr = rffi.cast(llmemory.Address, 123456789 + i)
        gcrootmap.put(retaddr, shapeaddr)
    for i in range(1, 600):
        expected_retaddr = rffi.cast(llmemory.Address, 123456789 + i)
        assert gcrootmap._gcmap[i*2+0] == expected_retaddr
        assert gcrootmap._gcmap[i*2+1] == expected_shapeaddr[i]

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
            assert x.next.foo == 101
            total = 0
            y = x
            for j in range(101):
                y = y.next
                total += y.foo
            assert not y.next
            assert total == 101*102/2
            n -= x.foo
    x_test = X()
    x_test.foo = 5
    main(6, x_test)     # check that it does not raise AssertionError
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
        assert counter.cnt < 5
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
        assert len(s) == 1*5 + 2*45 + 3*450 + 4*500
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
                assert len(l) == 3
                assert l[0] == n
                assert l[1] == n
                assert l[2] == n
            n -= x.foo
        assert len(l) == 3
        assert l[0] == 2
        assert l[1] == 2
        assert l[2] == 2
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
                assert l[0].x == 123
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
                assert len(l) == 16
                assert l[0].x == 123
                assert l[1].x == n
                assert l[2].x == n+10
                assert l[3].x == n+20
                assert l[4].x == n+30
                assert l[5].x == n+40
                assert l[6].x == n+50
                assert l[7].x == n+60
                assert l[8].x == n+70
                assert l[9].x == n+80
                assert l[10].x == n+90
                assert l[11].x == n+100
                assert l[12].x == n+110
                assert l[13].x == n+120
                assert l[14].x == n+130
                assert l[15].x == n+140
            n -= x.foo
        assert len(l) == 16
        assert l[0].x == 123
        assert l[1].x == 2
        assert l[2].x == 12
        assert l[3].x == 22
        assert l[4].x == 32
        assert l[5].x == 42
        assert l[6].x == 52
        assert l[7].x == 62
        assert l[8].x == 72
        assert l[9].x == 82
        assert l[10].x == 92
        assert l[11].x == 102
        assert l[12].x == 112
        assert l[13].x == 122
        assert l[14].x == 132
        assert l[15].x == 142
    res = compile_and_run(get_test(main), "hybrid", gcrootfinder="asmgcc",
                          jit=True)
    assert int(res) == 20
