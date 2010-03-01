"""
This is a test that translates a complete JIT to C and runs it.  It is
not testing much, expect that it basically works.  What it *is* testing,
however, is the correct handling of GC, i.e. if objects are freed as
soon as possible (at least in a simple case).
"""

import weakref, random
import py
from pypy.annotation import policy as annpolicy
from pypy.rlib import rgc
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.jit import JitDriver, OPTIMIZER_SIMPLE, dont_look_inside
from pypy.rlib.jit import purefunction
from pypy.jit.backend.x86.runner import CPU386
from pypy.jit.backend.llsupport.gc import GcRefList, GcRootMap_asmgcc
from pypy.tool.udir import udir

class X(object):
    def __init__(self, x=0):
        self.x = x

    next = None

class CheckError(Exception):
    pass

def check(flag):
    if not flag:
        raise CheckError

def get_g(main):
    main._dont_inline_ = True
    def g(name, n):
        x = X()
        x.foo = 2
        main(n, x)
        x.foo = 5
        return weakref.ref(x)
    g._dont_inline_ = True
    return g


def get_entry(g):

    def entrypoint(args):
        name = ''
        n = 2000
        argc = len(args)
        if argc > 1:
            name = args[1]
        if argc > 2:
            n = int(args[2])
        r_list = []
        for i in range(20):
            r = g(name, n)
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


def compile(f, gc, **kwds):
    from pypy.annotation.listdef import s_list_of_strings
    from pypy.translator.translator import TranslationContext
    from pypy.jit.metainterp.warmspot import apply_jit
    from pypy.translator.c import genc
    #
    t = TranslationContext()
    t.config.translation.gc = gc
    if gc != 'boehm':
        t.config.translation.gcremovetypeptr = True
    for name, value in kwds.items():
        setattr(t.config.translation, name, value)
    ann = t.buildannotator(policy=annpolicy.StrictAnnotatorPolicy())
    ann.build_types(f, [s_list_of_strings])
    t.buildrtyper().specialize()
    if kwds['jit']:
        apply_jit(t, optimizer=OPTIMIZER_SIMPLE)
    cbuilder = genc.CStandaloneBuilder(t, f, t.config)
    cbuilder.generate_source()
    cbuilder.compile()
    return cbuilder

def run(cbuilder, args=''):
    #
    pypylog = udir.join('test_zrpy_gc.log')
    data = cbuilder.cmdexec(args, env={'PYPYLOG': str(pypylog)})
    return data.strip()

def compile_and_run(f, gc, **kwds):
    cbuilder = compile(f, gc, **kwds)
    return run(cbuilder)



def test_compile_boehm():
    myjitdriver = JitDriver(greens = [], reds = ['n', 'x'])
    def main(n, x):
        while n > 0:
            myjitdriver.can_enter_jit(n=n, x=x)
            myjitdriver.jit_merge_point(n=n, x=x)
            y = X()
            y.foo = x.foo
            n -= y.foo
    res = compile_and_run(get_entry(get_g(main)), "boehm", jit=True)
    assert int(res) >= 16

# ______________________________________________________________________

class TestCompileHybrid(object):
    def setup_class(cls):
        funcs = []
        name_to_func = {}
        for fullname in dir(cls):
            if not fullname.startswith('define'):
                continue
            definefunc = getattr(cls, fullname)
            _, name = fullname.split('_', 1)
            beforefunc, loopfunc, afterfunc = definefunc.im_func(cls)
            if beforefunc is None:
                def beforefunc(n, x):
                    return n, x, None, None, None, None, None, None, None, None, None, ''
            if afterfunc is None:
                def afterfunc(n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s):
                    pass
            beforefunc.func_name = 'before_'+name
            loopfunc.func_name = 'loop_'+name
            afterfunc.func_name = 'after_'+name
            funcs.append((beforefunc, loopfunc, afterfunc))
            assert name not in name_to_func
            name_to_func[name] = len(name_to_func)
        print name_to_func
        def allfuncs(name, n):
            x = X()
            x.foo = 2
            main_allfuncs(name, n, x)
            x.foo = 5
            return weakref.ref(x)
        def main_allfuncs(name, n, x):
            num = name_to_func[name]            
            n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s = funcs[num][0](n, x)
            while n > 0:
                myjitdriver.can_enter_jit(num=num, n=n, x=x, x0=x0, x1=x1,
                        x2=x2, x3=x3, x4=x4, x5=x5, x6=x6, x7=x7, l=l, s=s)
                myjitdriver.jit_merge_point(num=num, n=n, x=x, x0=x0, x1=x1,
                        x2=x2, x3=x3, x4=x4, x5=x5, x6=x6, x7=x7, l=l, s=s)

                n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s = funcs[num][1](
                        n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s)
            funcs[num][2](n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s)
        myjitdriver = JitDriver(greens = ['num'],
                                reds = ['n', 'x', 'x0', 'x1', 'x2', 'x3', 'x4',
                                        'x5', 'x6', 'x7', 'l', 's'])
        cls.main_allfuncs = staticmethod(main_allfuncs)
        cls.name_to_func = name_to_func
        cls.cbuilder = compile(get_entry(allfuncs), "hybrid", gcrootfinder="asmgcc", jit=True)

    def run(self, name, n=2000):
        pypylog = udir.join('TestCompileHybrid.log')
        res = self.cbuilder.cmdexec("%s %d" %(name, n),
                                    env={'PYPYLOG': str(pypylog)})
        assert int(res) == 20

    def run_orig(self, name, n, x):
        self.main_allfuncs(name, n, x)

    def define_compile_hybrid_1(cls):
        # a moving GC.  Supports malloc_varsize_nonmovable.  Simple test, works
        # without write_barriers and root stack enumeration.
        def f(n, x, *args):
            y = X()
            y.foo = x.foo
            n -= y.foo
            return (n, x) + args
        return None, f, None

    def test_compile_hybrid_1(self):
        self.run('compile_hybrid_1')

    def define_compile_hybrid_2(cls):
        # More complex test, requires root stack enumeration but
        # not write_barriers.
        def f(n, x, *args):
            prev = x
            for j in range(101):    # f() runs 20'000 times, thus allocates
                y = X()             # a total of 2'020'000 objects
                y.foo = prev.foo
                prev = y
            n -= prev.foo
            return (n, x) + args
        return None, f, None

    def test_compile_hybrid_2(self):
        self.run('compile_hybrid_2')

    def define_compile_hybrid_3(cls):
        # Third version of the test.  Really requires write_barriers.
        def f(n, x, *args):
            x.next = None
            for j in range(101):    # f() runs 20'000 times, thus allocates
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
            return (n, x) + args
        return None, f, None



    def test_compile_hybrid_3(self):
        x_test = X()
        x_test.foo = 5
        self.run_orig('compile_hybrid_3', 6, x_test)     # check that it does not raise CheckError
        self.run('compile_hybrid_3')

    def define_compile_hybrid_3_extra(cls):
        # Extra version of the test, with tons of live vars around the residual
        # call that all contain a GC pointer.
        @dont_look_inside
        def residual(n=26):
            x = X()
            x.next = X()
            x.next.foo = n
            return x
        #
        def before(n, x):
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
            return n, None, x0, x1, x2, x3, x4, x5, x6, x7, None, None
        def f(n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s):
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
            return n, None, x0, x1, x2, x3, x4, x5, x6, x7, None, None
        return before, f, None

    def test_compile_hybrid_3_extra(self):
        self.run_orig('compile_hybrid_3_extra', 6, None)     # check that it does not raise CheckError
        self.run('compile_hybrid_3_extra')

    def define_compile_hybrid_4(cls):
        # Fourth version of the test, with __del__.
        from pypy.rlib.debug import debug_print
        class Counter:
            cnt = 0
        counter = Counter()
        class Z:
            def __del__(self):
                counter.cnt -= 1
        def before(n, x):
            debug_print('counter.cnt =', counter.cnt)
            check(counter.cnt < 5)
            counter.cnt = n // x.foo
            return n, x, None, None, None, None, None, None, None, None, None, None
        def f(n, x, *args):
            Z()
            n -= x.foo
            return (n, x) + args
        return before, f, None

    def test_compile_hybrid_4(self):
        self.run('compile_hybrid_4')

    def define_compile_hybrid_5(cls):
        # Test string manipulation.
        def f(n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s):
            n -= x.foo
            s += str(n)
            return n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s
        def after(n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s):
            check(len(s) == 1*5 + 2*45 + 3*450 + 4*500)
        return None, f, after

    def test_compile_hybrid_5(self):
        self.run('compile_hybrid_5')

    def define_compile_hybrid_7(cls):
        # Array of pointers (test the write barrier for setarrayitem_gc)
        def before(n, x):
            return n, x, None, None, None, None, None, None, None, None, [X(123)], None
        def f(n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s):
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
            return n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s
        def after(n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s):
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
        return before, f, after

    def test_compile_hybrid_7(self):
        self.run('compile_hybrid_7')

    def define_compile_hybrid_external_exception_handling(cls):
        def before(n, x):
            x = X(0)
            return n, x, None, None, None, None, None, None, None, None, None, None        

        @dont_look_inside
        def g(x):
            if x > 200:
                return 2
            raise ValueError
        @dont_look_inside
        def h(x):
            if x > 150:
                raise ValueError
            return 2

        def f(n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s):
            try:
                x.x += g(n)
            except ValueError:
                x.x += 1
            try:
                x.x += h(n)
            except ValueError:
                x.x -= 1
            n -= 1
            return n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s

        def after(n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s):
            check(x.x == 1800 * 2 + 1850 * 2 + 200 - 150)

        return before, f, None

    def test_compile_hybrid_external_exception_handling(self):
        self.run('compile_hybrid_external_exception_handling')
            
    def define_compile_hybrid_bug1(self):
        @purefunction
        def nonmoving():
            x = X(1)
            for i in range(7):
                rgc.collect()
            return x

        @dont_look_inside
        def do_more_stuff():
            x = X(5)
            for i in range(7):
                rgc.collect()
            return x

        def f(n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s):
            x0 = do_more_stuff()
            check(nonmoving().x == 1)
            n -= 1
            return n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s

        return None, f, None

    def test_compile_hybrid_bug1(self):
        self.run('compile_hybrid_bug1', 200)

    def define_compile_hybrid_vref(self):
        from pypy.rlib.jit import virtual_ref, virtual_ref_finish
        class A:
            pass
        glob = A()
        def f(n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s):
            a = A()
            glob.v = virtual_ref(a)
            virtual_ref_finish(a)
            n -= 1
            return n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s
        return None, f, None

    def test_compile_hybrid_vref(self):
        self.run('compile_hybrid_vref', 200)
