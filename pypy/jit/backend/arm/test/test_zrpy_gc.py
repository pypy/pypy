"""
This is a test that translates a complete JIT to C and runs it.  It is
not testing much, expect that it basically works.  What it *is* testing,
however, is the correct handling of GC, i.e. if objects are freed as
soon as possible (at least in a simple case).
"""

import weakref
import py, os
from pypy.annotation import policy as annpolicy
from pypy.rlib import rgc
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.jit import JitDriver, dont_look_inside
from pypy.rlib.jit import purefunction, unroll_safe
from pypy.jit.backend.arm.runner import ArmCPU
from pypy.jit.backend.llsupport.gc import GcRefList, GcRootMap_asmgcc
from pypy.jit.backend.llsupport.gc import GcLLDescr_framework
from pypy.tool.udir import udir
from pypy.config.translationoption import DEFL_GC
import py.test

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


def get_functions_to_patch():
    from pypy.jit.backend.llsupport import gc
    #
    can_inline_malloc1 = gc.GcLLDescr_framework.can_inline_malloc
    def can_inline_malloc2(*args):
        try:
            if os.environ['PYPY_NO_INLINE_MALLOC']:
                return False
        except KeyError:
            pass
        return can_inline_malloc1(*args)
    #
    return {(gc.GcLLDescr_framework, 'can_inline_malloc'): can_inline_malloc2}

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
    ann.build_types(f, [s_list_of_strings], main_entry_point=True)
    t.buildrtyper().specialize()

    if kwds['jit']:
        patch = get_functions_to_patch()
        old_value = {}
        try:
            for (obj, attr), value in patch.items():
                old_value[obj, attr] = getattr(obj, attr)
                setattr(obj, attr, value)
            #
            apply_jit(t, enable_opts='')
            #
        finally:
            for (obj, attr), oldvalue in old_value.items():
                setattr(obj, attr, oldvalue)

    cbuilder = genc.CStandaloneBuilder(t, f, t.config)
    cbuilder.generate_source()
    cbuilder.compile()
    return cbuilder

def run(cbuilder, args=''):
    #
    pypylog = udir.join('test_zrpy_gc.log')
    data = cbuilder.cmdexec(args, env={'PYPYLOG': ':%s' % pypylog})
    return data.strip()

def compile_and_run(f, gc, **kwds):
    cbuilder = compile(f, gc, **kwds)
    return run(cbuilder)



def test_compile_boehm():
    myjitdriver = JitDriver(greens = [], reds = ['n', 'x'])
    @dont_look_inside
    def see(lst, n):
        assert len(lst) == 3
        assert lst[0] == n+10
        assert lst[1] == n+20
        assert lst[2] == n+30
    def main(n, x):
        while n > 0:
            myjitdriver.can_enter_jit(n=n, x=x)
            myjitdriver.jit_merge_point(n=n, x=x)
            y = X()
            y.foo = x.foo
            n -= y.foo
            see([n+10, n+20, n+30], n)
    res = compile_and_run(get_entry(get_g(main)), "boehm", jit=True)
    assert int(res) >= 16

# ______________________________________________________________________

class CompileFrameworkTests(object):
    # Test suite using (so far) the minimark GC.
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
        OLD_DEBUG = GcLLDescr_framework.DEBUG
        try:
            GcLLDescr_framework.DEBUG = True
            cls.cbuilder = compile(get_entry(allfuncs), DEFL_GC,
                                   gcrootfinder=cls.gcrootfinder, jit=True)
        finally:
            GcLLDescr_framework.DEBUG = OLD_DEBUG

    def _run(self, name, n, env):
        res = self.cbuilder.cmdexec("%s %d" %(name, n), env=env)
        assert int(res) == 20

    def run(self, name, n=2000):
        pypylog = udir.join('TestCompileFramework.log')
        env = {'PYPYLOG': ':%s' % pypylog,
               'PYPY_NO_INLINE_MALLOC': '1'}
        self._run(name, n, env)
        env['PYPY_NO_INLINE_MALLOC'] = ''
        self._run(name, n, env)

    def run_orig(self, name, n, x):
        self.main_allfuncs(name, n, x)

    def define_libffi_workaround(cls):
        # XXX: this is a workaround for a bug in database.py.  It seems that
        # the problem is triggered by optimizeopt/fficall.py, and in
        # particular by the ``cast_base_ptr_to_instance(Func, llfunc)``: in
        # these tests, that line is the only place where libffi.Func is
        # referenced.
        #
        # The problem occurs because the gctransformer tries to annotate a
        # low-level helper to call the __del__ of libffi.Func when it's too
        # late.
        #
        # This workaround works by forcing the annotator (and all the rest of
        # the toolchain) to see libffi.Func in a "proper" context, not just as
        # the target of cast_base_ptr_to_instance.  Note that the function
        # below is *never* called by any actual test, it's just annotated.
        #
        from pypy.rlib.libffi import get_libc_name, CDLL, types, ArgChain
        libc_name = get_libc_name()
        def f(n, x, *args):
            libc = CDLL(libc_name)
            ptr = libc.getpointer('labs', [types.slong], types.slong)
            chain = ArgChain()
            chain.arg(n)
            n = ptr.call(chain, lltype.Signed)
            return (n, x) + args
        return None, f, None

    def define_compile_framework_1(cls):
        # a moving GC.  Supports malloc_varsize_nonmovable.  Simple test, works
        # without write_barriers and root stack enumeration.
        def f(n, x, *args):
            y = X()
            y.foo = x.foo
            n -= y.foo
            return (n, x) + args
        return None, f, None

    def test_compile_framework_1(self):
        self.run('compile_framework_1')

    def define_compile_framework_2(cls):
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

    def test_compile_framework_2(self):
        self.run('compile_framework_2')

    def define_compile_framework_3(cls):
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



    def test_compile_framework_3(self):
        x_test = X()
        x_test.foo = 5
        self.run_orig('compile_framework_3', 6, x_test)     # check that it does not raise CheckError
        self.run('compile_framework_3')

    def define_compile_framework_3_extra(cls):
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

    def test_compile_framework_3_extra(self):
        self.run_orig('compile_framework_3_extra', 6, None)     # check that it does not raise CheckError
        self.run('compile_framework_3_extra')

    def define_compile_framework_4(cls):
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

    def test_compile_framework_4(self):
        self.run('compile_framework_4')

    def define_compile_framework_5(cls):
        # Test string manipulation.
        def f(n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s):
            n -= x.foo
            s += str(n)
            return n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s
        def after(n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s):
            check(len(s) == 1*5 + 2*45 + 3*450 + 4*500)
        return None, f, after

    def test_compile_framework_5(self):
        self.run('compile_framework_5')

    def define_compile_framework_7(cls):
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

    def test_compile_framework_7(self):
        self.run('compile_framework_7')

    def define_compile_framework_external_exception_handling(cls):
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

    def test_compile_framework_external_exception_handling(self):
        self.run('compile_framework_external_exception_handling')

    def define_compile_framework_bug1(self):
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

    def test_compile_framework_bug1(self):
        self.run('compile_framework_bug1', 200)

    def define_compile_framework_vref(self):
        from pypy.rlib.jit import virtual_ref, virtual_ref_finish
        class A:
            pass
        glob = A()
        def f(n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s):
            a = A()
            glob.v = vref = virtual_ref(a)
            virtual_ref_finish(vref, a)
            n -= 1
            return n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s
        return None, f, None

    def test_compile_framework_vref(self):
        self.run('compile_framework_vref', 200)

    def define_compile_framework_float(self):
        # test for a bug: the fastpath_malloc does not save and restore
        # xmm registers around the actual call to the slow path
        class A:
            x0 = x1 = x2 = x3 = x4 = x5 = x6 = x7 = 0
        @dont_look_inside
        def escape1(a):
            a.x0 += 0
            a.x1 += 6
            a.x2 += 12
            a.x3 += 18
            a.x4 += 24
            a.x5 += 30
            a.x6 += 36
            a.x7 += 42
        @dont_look_inside
        def escape2(n, f0, f1, f2, f3, f4, f5, f6, f7):
            check(f0 == n + 0.0)
            check(f1 == n + 0.125)
            check(f2 == n + 0.25)
            check(f3 == n + 0.375)
            check(f4 == n + 0.5)
            check(f5 == n + 0.625)
            check(f6 == n + 0.75)
            check(f7 == n + 0.875)
        @unroll_safe
        def f(n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s):
            i = 0
            while i < 42:
                m = n + i
                f0 = m + 0.0
                f1 = m + 0.125
                f2 = m + 0.25
                f3 = m + 0.375
                f4 = m + 0.5
                f5 = m + 0.625
                f6 = m + 0.75
                f7 = m + 0.875
                a1 = A()
                # at this point, all or most f's are still in xmm registers
                escape1(a1)
                escape2(m, f0, f1, f2, f3, f4, f5, f6, f7)
                i += 1
            n -= 1
            return n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s
        return None, f, None

    def test_compile_framework_float(self):
        self.run('compile_framework_float')

    def define_compile_framework_minimal_size_in_nursery(self):
        S = lltype.GcStruct('S')    # no fields!
        T = lltype.GcStruct('T', ('i', lltype.Signed))
        @unroll_safe
        def f42(n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s):
            lst1 = []
            lst2 = []
            i = 0
            while i < 42:
                s1 = lltype.malloc(S)
                t1 = lltype.malloc(T)
                t1.i = 10000 + i + n
                lst1.append(s1)
                lst2.append(t1)
                i += 1
            i = 0
            while i < 42:
                check(lst2[i].i == 10000 + i + n)
                i += 1
            n -= 1
            return n, x, x0, x1, x2, x3, x4, x5, x6, x7, l, s
        return None, f42, None

    def test_compile_framework_minimal_size_in_nursery(self):
        self.run('compile_framework_minimal_size_in_nursery')


class TestShadowStack(CompileFrameworkTests):
    gcrootfinder = "shadowstack"
