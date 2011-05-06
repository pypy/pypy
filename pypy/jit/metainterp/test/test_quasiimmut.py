
import py

from pypy.rpython.lltypesystem import lltype, llmemory, rclass
from pypy.rpython.rclass import FieldListAccessor, IR_QUASIIMMUTABLE
from pypy.jit.metainterp import typesystem
from pypy.jit.metainterp.quasiimmut import QuasiImmut
from pypy.jit.metainterp.quasiimmut import get_current_qmut_instance
from pypy.jit.metainterp.test.support import LLJitMixin
from pypy.jit.codewriter.policy import StopAtXPolicy
from pypy.rlib.jit import JitDriver, dont_look_inside


def test_get_current_qmut_instance():
    accessor = FieldListAccessor()
    accessor.initialize(None, {'inst_x': IR_QUASIIMMUTABLE})
    STRUCT = lltype.GcStruct('Foo', ('inst_x', lltype.Signed),
                             ('mutate_x', rclass.OBJECTPTR),
                             hints={'immutable_fields': accessor})
    foo = lltype.malloc(STRUCT, zero=True)
    foo.inst_x = 42
    assert not foo.mutate_x

    class FakeCPU:
        ts = typesystem.llhelper

        def bh_getfield_gc_r(self, gcref, fielddescr):
            assert fielddescr == mutatefielddescr
            foo = lltype.cast_opaque_ptr(lltype.Ptr(STRUCT), gcref)
            result = foo.mutate_x
            return lltype.cast_opaque_ptr(llmemory.GCREF, result)

        def bh_setfield_gc_r(self, gcref, fielddescr, newvalue_gcref):
            assert fielddescr == mutatefielddescr
            foo = lltype.cast_opaque_ptr(lltype.Ptr(STRUCT), gcref)
            newvalue = lltype.cast_opaque_ptr(rclass.OBJECTPTR, newvalue_gcref)
            foo.mutate_x = newvalue

    cpu = FakeCPU()
    mutatefielddescr = ('fielddescr', STRUCT, 'mutate_x')

    foo_gcref = lltype.cast_opaque_ptr(llmemory.GCREF, foo)
    qmut1 = get_current_qmut_instance(cpu, foo_gcref, mutatefielddescr)
    assert isinstance(qmut1, QuasiImmut)
    qmut2 = get_current_qmut_instance(cpu, foo_gcref, mutatefielddescr)
    assert qmut1 is qmut2


class QuasiImmutTests(object):

    def test_simple_1(self):
        myjitdriver = JitDriver(greens=['foo'], reds=['x', 'total'])
        class Foo:
            _immutable_fields_ = ['a?']
            def __init__(self, a):
                self.a = a
        def f(a, x):
            foo = Foo(a)
            total = 0
            while x > 0:
                myjitdriver.jit_merge_point(foo=foo, x=x, total=total)
                # read a quasi-immutable field out of a Constant
                total += foo.a
                x -= 1
            return total
        #
        res = self.meta_interp(f, [100, 7])
        assert res == 700
        self.check_loops(guard_not_invalidated=2, getfield_gc=0,
                         everywhere=True)
        #
        from pypy.jit.metainterp.warmspot import get_stats
        loops = get_stats().loops
        for loop in loops:
            assert len(loop.quasi_immutable_deps) == 1
            assert isinstance(loop.quasi_immutable_deps.keys()[0], QuasiImmut)

    def test_nonopt_1(self):
        myjitdriver = JitDriver(greens=[], reds=['x', 'total', 'lst'])
        class Foo:
            _immutable_fields_ = ['a?']
            def __init__(self, a):
                self.a = a
        def setup(x):
            return [Foo(100 + i) for i in range(x)]
        def f(a, x):
            lst = setup(x)
            total = 0
            while x > 0:
                myjitdriver.jit_merge_point(lst=lst, x=x, total=total)
                # read a quasi-immutable field out of a variable
                x -= 1
                total += lst[x].a
            return total
        #
        assert f(100, 7) == 721
        res = self.meta_interp(f, [100, 7])
        assert res == 721
        self.check_loops(guard_not_invalidated=0, getfield_gc=1)
        #
        from pypy.jit.metainterp.warmspot import get_stats
        loops = get_stats().loops
        for loop in loops:
            assert loop.quasi_immutable_deps is None

    def test_opt_via_virtual_1(self):
        myjitdriver = JitDriver(greens=['foo'], reds=['x', 'total'])
        class Foo:
            _immutable_fields_ = ['a?']
            def __init__(self, a):
                self.a = a
        class A:
            pass
        def f(a, x):
            foo = Foo(a)
            total = 0
            while x > 0:
                myjitdriver.jit_merge_point(foo=foo, x=x, total=total)
                # make it a Constant after optimization only
                a = A()
                a.foo = foo
                foo = a.foo
                # read a quasi-immutable field out of it
                total += foo.a
                x -= 1
            return total
        #
        res = self.meta_interp(f, [100, 7])
        assert res == 700
        self.check_loops(guard_not_invalidated=2, getfield_gc=0,
                         everywhere=True)

    def test_change_during_tracing_1(self):
        myjitdriver = JitDriver(greens=['foo'], reds=['x', 'total'])
        class Foo:
            _immutable_fields_ = ['a?']
            def __init__(self, a):
                self.a = a
        @dont_look_inside
        def residual_call(foo):
            foo.a += 1
        def f(a, x):
            foo = Foo(a)
            total = 0
            while x > 0:
                myjitdriver.jit_merge_point(foo=foo, x=x, total=total)
                # read a quasi-immutable field out of a Constant
                total += foo.a
                residual_call(foo)
                x -= 1
            return total
        #
        assert f(100, 7) == 721
        res = self.meta_interp(f, [100, 7])
        assert res == 721
        self.check_loops(guard_not_invalidated=0, getfield_gc=1)

    def test_change_during_tracing_2(self):
        myjitdriver = JitDriver(greens=['foo'], reds=['x', 'total'])
        class Foo:
            _immutable_fields_ = ['a?']
            def __init__(self, a):
                self.a = a
        @dont_look_inside
        def residual_call(foo, difference):
            foo.a += difference
        def f(a, x):
            foo = Foo(a)
            total = 0
            while x > 0:
                myjitdriver.jit_merge_point(foo=foo, x=x, total=total)
                # read a quasi-immutable field out of a Constant
                total += foo.a
                residual_call(foo, +1)
                residual_call(foo, -1)
                x -= 1
            return total
        #
        assert f(100, 7) == 700
        res = self.meta_interp(f, [100, 7])
        assert res == 700
        self.check_loops(guard_not_invalidated=0, getfield_gc=1)

    def test_change_invalidate_reentering(self):
        myjitdriver = JitDriver(greens=['foo'], reds=['x', 'total'])
        class Foo:
            _immutable_fields_ = ['a?']
            def __init__(self, a):
                self.a = a
        def f(foo, x):
            total = 0
            while x > 0:
                myjitdriver.jit_merge_point(foo=foo, x=x, total=total)
                # read a quasi-immutable field out of a Constant
                total += foo.a
                x -= 1
            return total
        def g(a, x):
            foo = Foo(a)
            res1 = f(foo, x)
            foo.a += 1          # invalidation, while the jit is not running
            res2 = f(foo, x)    # should still mark the loop as invalid
            return res1 * 1000 + res2
        #
        assert g(100, 7) == 700707
        res = self.meta_interp(g, [100, 7])
        assert res == 700707
        self.check_loops(guard_not_invalidated=2, getfield_gc=0)

    def test_invalidate_while_running(self):
        jitdriver = JitDriver(greens=['foo'], reds=['i', 'total'])

        class Foo(object):
            _immutable_fields_ = ['a?']
            def __init__(self, a):
                self.a = a

        def external(foo, v):
            if v:
                foo.a = 2

        def f(foo):
            i = 0
            total = 0
            while i < 10:
                jitdriver.jit_merge_point(i=i, foo=foo, total=total)
                external(foo, i > 7)
                i += 1
                total += foo.a
            return total

        def g():
            return f(Foo(1))

        assert self.meta_interp(g, [], policy=StopAtXPolicy(external)) == g()

    def test_invalidate_by_setfield(self):
        jitdriver = JitDriver(greens=['bc', 'foo'], reds=['i', 'total'])

        class Foo(object):
            _immutable_fields_ = ['a?']
            def __init__(self, a):
                self.a = a

        def f(foo, bc):
            i = 0
            total = 0
            while i < 10:
                jitdriver.jit_merge_point(bc=bc, i=i, foo=foo, total=total)
                if bc == 0:
                    f(foo, 1)
                if bc == 1:
                    foo.a = int(i > 5)
                i += 1
                total += foo.a
            return total

        def g():
            return f(Foo(1), 0)

        assert self.meta_interp(g, []) == g()

    def test_invalidate_bridge(self):
        jitdriver = JitDriver(greens=['foo'], reds=['i', 'total'])

        class Foo(object):
            _immutable_fields_ = ['a?']

        def f(foo):
            i = 0
            total = 0
            while i < 10:
                jitdriver.jit_merge_point(i=i, total=total, foo=foo)
                if i > 5:
                    total += foo.a
                else:
                    total += 2*foo.a
                i += 1
            return total

        def main():
            foo = Foo()
            foo.a = 1
            total = f(foo)
            foo.a = 2
            total += f(foo)
            foo.a = 1
            total += f(foo)
            return total

        res = self.meta_interp(main, [])
        self.check_loop_count(7)
        assert res == main()

    def test_change_during_running(self):
        myjitdriver = JitDriver(greens=['foo'], reds=['x', 'total'])
        class Foo:
            _immutable_fields_ = ['a?']
            def __init__(self, a):
                self.a = a
        @dont_look_inside
        def residual_call(foo, x):
            if x == 5:
                foo.a += 1
        def f(a, x):
            foo = Foo(a)
            total = 0
            while x > 0:
                myjitdriver.jit_merge_point(foo=foo, x=x, total=total)
                # read a quasi-immutable field out of a Constant
                total += foo.a
                residual_call(foo, x)
                total += foo.a
                x -= 1
            return total
        #
        assert f(100, 15) == 3009
        res = self.meta_interp(f, [100, 15])
        assert res == 3009
        self.check_loops(guard_not_invalidated=2, getfield_gc=0,
                         call_may_force=0, guard_not_forced=0)

    def test_list_simple_1(self):
        myjitdriver = JitDriver(greens=['foo'], reds=['x', 'total'])
        class Foo:
            _immutable_fields_ = ['lst?[*]']
            def __init__(self, lst):
                self.lst = lst
        def f(a, x):
            lst1 = [0, 0]
            lst1[1] = a
            foo = Foo(lst1)
            total = 0
            while x > 0:
                myjitdriver.jit_merge_point(foo=foo, x=x, total=total)
                # read a quasi-immutable field out of a Constant
                total += foo.lst[1]
                x -= 1
            return total
        #
        res = self.meta_interp(f, [100, 7])
        assert res == 700
        self.check_loops(guard_not_invalidated=2, getfield_gc=0,
                         getarrayitem_gc=0, getarrayitem_gc_pure=0,
                         everywhere=True)
        #
        from pypy.jit.metainterp.warmspot import get_stats
        loops = get_stats().loops
        for loop in loops:
            assert len(loop.quasi_immutable_deps) == 1
            assert isinstance(loop.quasi_immutable_deps.keys()[0], QuasiImmut)

    def test_list_length_1(self):
        myjitdriver = JitDriver(greens=['foo'], reds=['x', 'total'])
        class Foo:
            _immutable_fields_ = ['lst?[*]']
            def __init__(self, lst):
                self.lst = lst
        class A:
            pass
        def f(a, x):
            lst1 = [0, 0]
            lst1[1] = a
            foo = Foo(lst1)
            total = 0
            while x > 0:
                myjitdriver.jit_merge_point(foo=foo, x=x, total=total)
                # make it a Constant after optimization only
                a = A()
                a.foo = foo
                foo = a.foo
                # read a quasi-immutable field out of it
                total += foo.lst[1]
                # also read the length
                total += len(foo.lst)
                x -= 1
            return total
        #
        res = self.meta_interp(f, [100, 7])
        assert res == 714
        self.check_loops(guard_not_invalidated=2, getfield_gc=0,
                         getarrayitem_gc=0, getarrayitem_gc_pure=0,
                         arraylen_gc=0, everywhere=True)
        #
        from pypy.jit.metainterp.warmspot import get_stats
        loops = get_stats().loops
        for loop in loops:
            assert len(loop.quasi_immutable_deps) == 1
            assert isinstance(loop.quasi_immutable_deps.keys()[0], QuasiImmut)

    def test_list_pass_around(self):
        py.test.skip("think about a way to fix it")
        myjitdriver = JitDriver(greens=['foo'], reds=['x', 'total'])
        class Foo:
            _immutable_fields_ = ['lst?[*]']
            def __init__(self, lst):
                self.lst = lst
        def g(lst):
            # here, 'lst' is statically annotated as a "modified" list,
            # so the following doesn't generate a getarrayitem_gc_pure...
            return lst[1]
        def f(a, x):
            lst1 = [0, 0]
            g(lst1)
            lst1[1] = a
            foo = Foo(lst1)
            total = 0
            while x > 0:
                myjitdriver.jit_merge_point(foo=foo, x=x, total=total)
                # read a quasi-immutable field out of a Constant
                total += g(foo.lst)
                x -= 1
            return total
        #
        res = self.meta_interp(f, [100, 7])
        assert res == 700
        self.check_loops(guard_not_invalidated=2, getfield_gc=0,
                         getarrayitem_gc=0, getarrayitem_gc_pure=0,
                         everywhere=True)
        #
        from pypy.jit.metainterp.warmspot import get_stats
        loops = get_stats().loops
        for loop in loops:
            assert len(loop.quasi_immutable_deps) == 1
            assert isinstance(loop.quasi_immutable_deps.keys()[0], QuasiImmut)

    def test_list_change_during_running(self):
        myjitdriver = JitDriver(greens=['foo'], reds=['x', 'total'])
        class Foo:
            _immutable_fields_ = ['lst?[*]']
            def __init__(self, lst):
                self.lst = lst
        @dont_look_inside
        def residual_call(foo, x):
            if x == 5:
                lst2 = [0, 0]
                lst2[1] = foo.lst[1] + 1
                foo.lst = lst2
        def f(a, x):
            lst1 = [0, 0]
            lst1[1] = a
            foo = Foo(lst1)
            total = 0
            while x > 0:
                myjitdriver.jit_merge_point(foo=foo, x=x, total=total)
                # read a quasi-immutable field out of a Constant
                total += foo.lst[1]
                residual_call(foo, x)
                total += foo.lst[1]
                x -= 1
            return total
        #
        assert f(100, 15) == 3009
        res = self.meta_interp(f, [100, 15])
        assert res == 3009
        self.check_loops(guard_not_invalidated=2, getfield_gc=0,
                         getarrayitem_gc=0, getarrayitem_gc_pure=0,
                         call_may_force=0, guard_not_forced=0)


class TestLLtypeGreenFieldsTests(QuasiImmutTests, LLJitMixin):
    pass
