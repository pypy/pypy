import py
from pypy.translator.translator import TranslationContext
from pypy.translator.tool.cbuild import check_boehm_presence
from pypy.translator.c.genc import CExtModuleBuilder
from pypy import conftest

def setup_module(mod):
    if not check_boehm_presence():
        py.test.skip("Boehm GC not present")

class AbstractTestClass:
    
    # deal with cleanups
    def setup_method(self, meth):
        self._cleanups = []
    def teardown_method(self, meth):
        while self._cleanups:
            #print "CLEANUP"
            self._cleanups.pop()()

    def getcompiled(self, func):
        t = TranslationContext(simplifying=True)
        self.t = t
        # builds starting-types from func_defs 
        argstypelist = []
        if func.func_defaults:
            for spec in func.func_defaults:
                if isinstance(spec, tuple):
                    spec = spec[0] # use the first type only for the tests
                argstypelist.append(spec)
        a = t.buildannotator().build_types(func, argstypelist)
        t.buildrtyper().specialize()
        t.checkgraphs()
        def compile():
            cbuilder = CExtModuleBuilder(t, func, gcpolicy=self.gcpolicy)
            c_source_filename = cbuilder.generate_source()
            if conftest.option.view:
                t.view()
            cbuilder.compile()
            mod = cbuilder.isolated_import()
            self._cleanups.append(cbuilder.cleanup) # schedule cleanup after test
            return cbuilder.get_entry_point()
        return compile()


class TestUsingBoehm(AbstractTestClass):
    from pypy.translator.c.gc import BoehmGcPolicy as gcpolicy

    def test_malloc_a_lot(self):
        def malloc_a_lot():
            i = 0
            while i < 10:
                i += 1
                a = [1] * 10
                j = 0
                while j < 20:
                    j += 1
                    a.append(j)
        fn = self.getcompiled(malloc_a_lot)
        fn()

    def test__del__(self):
        from pypy.rpython.lltypesystem.lloperation import llop
        from pypy.rpython.lltypesystem import lltype
        class State:
            pass
        s = State()
        class A(object):
            def __del__(self):
                s.a_dels += 1
        class B(A):
            def __del__(self):
                s.b_dels += 1
        class C(A):
            pass
        def f():
            s.a_dels = 0
            s.b_dels = 0
            A()
            B()
            C()
            A()
            B()
            C()
            llop.gc__collect(lltype.Void)
            return s.a_dels * 10 + s.b_dels
        fn = self.getcompiled(f)
        # we can't demand that boehm has collected all of the objects,
        # even with the gc__collect call.  calling the compiled
        # function twice seems to help, though.
        res = 0
        res += fn()
        res += fn()
        # if res is still 0, then we haven't tested anything so fail.
        # it might be the test's fault though.
        assert 0 < res <= 84

    def test_weakgcaddress_is_weak(self):
        from pypy.rpython.lltypesystem.lloperation import llop
        from pypy.rpython.lltypesystem import lltype
        from pypy.rpython.objectmodel import cast_object_to_weakgcaddress
        class State:
            pass
        s = State()
        class A(object):
            def __del__(self):
                s.a_dels += 1
        def f(i=int):
            if i:
                s.a_dels = 0
                a = A()
                # this should not keep a alive
                s.a = cast_object_to_weakgcaddress(a)
            llop.gc__collect(lltype.Void)
            llop.gc__collect(lltype.Void)
            llop.gc__collect(lltype.Void)
            return s.a_dels
        fn = self.getcompiled(f)
        # we can't demand that boehm has collected all of the objects,
        # even with the gc__collect call.  calling the compiled
        # function twice seems to help, though.
        fn(1)
        fn(0)
        fn(0)
        res = fn(0)
        print res
        assert res == 1

    def test_del_raises(self):
        from pypy.rpython.lltypesystem.lloperation import llop
        from pypy.rpython.lltypesystem import lltype
        import os
        class A(object):
            def __del__(self):
                s.dels += 1
                raise Exception
        class State:
            pass
        s = State()
        s.dels = 0
        def g():
            a = A()            
        def f():
            s.dels = 0
            for i in range(10):
                g()
            llop.gc__collect(lltype.Void)
            return s.dels
        fn = self.getcompiled(f)
        # we can't demand that boehm has collected all of the objects,
        # even with the gc__collect call.  calling the compiled
        # function twice seems to help, though.
        res = 0
        res += fn()
        res += fn()
        # if res is still 0, then we haven't tested anything so fail.
        # it might be the test's fault though.
        assert res > 0

    def test_memory_error_varsize(self):
        from pypy.rpython.lltypesystem import lltype
        N = int(2**31-1)
        A = lltype.GcArray(lltype.Char)
        def alloc(n):
            return lltype.malloc(A, n)
        def f():
            try:
                x = alloc(N)
            except MemoryError:
                y = alloc(10)
                return len(y)
            y = alloc(10)
            return len(y) # allocation may work on 64 bits machines
        fn = self.getcompiled(f)
        res = fn()
        assert res == 10
        

class TestUsingExactBoehm(TestUsingBoehm):
    from pypy.translator.c.gc import MoreExactBoehmGcPolicy as gcpolicy


