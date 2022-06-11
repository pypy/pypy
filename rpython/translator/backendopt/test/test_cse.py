from rpython.translator.translator import TranslationContext, graphof
from rpython.translator.backendopt.cse import cse_graph
from rpython.translator.backendopt import removenoops
from rpython.flowspace.model import checkgraph, summary
from rpython.conftest import option

class TestCSE(object):
    def translate(self, func, argtypes):
        t = TranslationContext()
        t.buildannotator().build_types(func, argtypes)
        t.buildrtyper().specialize()
        return t

    def check(self, f, argtypes, fullopts=False, **expected):
        from rpython.translator.backendopt import inline, all, constfold
        t = self.translate(f, argtypes)
        getfields = 0
        graph = graphof(t, f)
        if option.view:
            t.view()
        if fullopts:
            all.backend_optimizations(t)
        removenoops.remove_same_as(graph)
        checkgraph(graph)
        cse_graph(graph)
        if option.view:
            t.view()
        checkgraph(graph)
        s = summary(graph)
        for key, val in expected.items():
            assert s.get(key, 0) == val
        assert "same_as" not in s

    def test_infrastructure(self):
        class A(object):
            pass

        def f(i):
            a = A()
            a.x = i
            return a.x

        self.check(f, [int], getfield=0)

    def test_simple(self):
        class A(object):
            pass

        def f(i):
            a = A()
            a.x = i
            return a.x + a.x

        self.check(f, [int], getfield=0)

    def test_irrelevant_setfield(self):
        class A(object):
            pass

        def f(i):
            a = A()
            a.x = i
            one = a.x
            a.y = 3
            two = a.x
            return one + two

        self.check(f, [int], getfield=0)

    def test_relevant_setfield(self):
        class A(object):
            pass

        def f(i):
            a = A()
            b = A()
            a.x = i
            b.x = i + 1
            one = a.x
            b.x = i
            two = a.x
            return one + two

        self.check(f, [int], getfield=2)

    def test_different_concretetype(self):
        class A(object):
            pass

        class B(object):
            pass

        def f(i):
            a = A()
            b = B()
            a.x = i
            one = a.x
            b.x = i + 1
            two = a.x
            return one + two

        self.check(f, [int], getfield=0)

    def test_subclass(self):
        class A(object):
            pass

        class B(A):
            pass

        def f(i):
            a = A()
            b = B()
            a.x = i
            one = a.x
            b.x = i + 1
            two = a.x
            return one + two

        self.check(f, [int], getfield=1)

    def test_bug_1(self):
        class A(object):
            pass

        def f(i):
            a = A()
            a.cond = i > 0
            n = a.cond
            if a.cond:
                return True
            return n

        self.check(f, [int], getfield=0)


    def test_cfg_splits(self):
        class A(object):
            pass

        def f(i):
            a = A()
            j = i
            for i in range(i):
                a.x = i
                if i:
                    j = a.x + a.x
                else:
                    j = a.x * 5
            return j

        self.check(f, [int], getfield=0)

    def test_malloc_does_not_invalidate(self):
        class A(object):
            pass
        class B(object):
            pass

        def f(i):
            a = A()
            a.x = i
            b = B()
            return a.x

        self.check(f, [int], getfield=0)

    def test_debug_assert_not_none(self):
        from rpython.rlib.debug import ll_assert_not_none
        class A(object):
            pass

        def g(i):
            if i:
                return None
            else:
                return A()

        def f(i):
            a1 = g(i)
            a = A()
            a.x = i
            ll_assert_not_none(a1)
            return a.x

        self.check(f, [int], getfield=0)

    def test_simple_intops(self):
        def f(i):
            x = (i + 1) * (i + 1)
            y = (i + 1) * (i + 1)
            return x - y

        # int_mul should be 1 too, but later
        self.check(f, [int], int_add=1, int_mul=1)

    def test_pure_split(self):
        def f(i, j):
            k = i + 1
            if j:
                return i + 1
            return k * (i + 1)

        self.check(f, [int, int], int_add=1)

    def test_two_getfields(self):
        class A(object):
            pass
        class B(object):
            pass
        a1 = A()
        a1.next = B()
        a1.next.x = 1
        a2 = A()
        a2.next = B()
        a2.next.x = 5


        def f(i):
            if i:
                a = a1
            else:
                a = a2
            return a.next.x + a.next.x + i

        self.check(f, [int], getfield=2)

    def test_cast_pointer(self):
        class Cls(object):
            pass
        class Sub(Cls):
            pass
        cls1 = Cls()
        cls2 = Sub()
        cls2.user_overridden_class = True
        cls3 = Sub()
        cls3.user_overridden_class = False
        class A(object):
            pass
        def f(i):
            a = A()
            return type(a) is A
        self.check(f, [int], getfield=0)
