from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.rlib import jit
from rpython.rtyper.lltypesystem import lltype, rffi


class TestCompatible(LLJitMixin):
    def test_simple(self):
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        p1 = lltype.malloc(S)
        p1.x = 5

        p2 = lltype.malloc(S)
        p2.x = 5

        p3 = lltype.malloc(S)
        p3.x = 6
        driver = jit.JitDriver(greens = [], reds = ['n', 'x'])

        class A(object):
            pass

        c = A()
        c.count = 0
        @jit.elidable_compatible()
        def g(s, ignored):
            c.count += 1
            return s.x

        def f(n, x):
            while n > 0:
                driver.can_enter_jit(n=n, x=x)
                driver.jit_merge_point(n=n, x=x)
                n -= g(x, "abc")

        def main():
            g(p1, "def") # make annotator not make argument constant
            f(100, p1)
            f(100, p2)
            f(100, p3)
            return c.count

        x = self.meta_interp(main, [])

        assert x < 30
        # trace, one bridge, a finish bridge
        self.check_trace_count(3)

    def test_simple_check_values(self):
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        p1 = lltype.malloc(S)
        p1.x = 5

        p2 = lltype.malloc(S)
        p2.x = 5

        p3 = lltype.malloc(S)
        p3.x = 6
        driver = jit.JitDriver(greens = [], reds = ['n', 's', 'x'])

        class A(object):
            pass

        c = A()
        c.count = 0
        @jit.elidable_compatible()
        def g(s, ignored):
            c.count += 1
            return s.x

        def f(n, x):
            s = 0
            while n > 0:
                driver.can_enter_jit(n=n, x=x, s=s)
                driver.jit_merge_point(n=n, x=x, s=s)
                diff = g(x, "abc")
                n -= 1
                s += diff
            return s

        def main():
            g(p1, "def") # make annotator not make argument constant
            n = f(100, p1)
            n += f(100, p2)
            n += f(100, p3)
            return n

        x = self.meta_interp(main, [])

        assert x == main()
        # trace, a bridge, a finish bridge
        self.check_trace_count(3)

    def test_exception(self):
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        p1 = lltype.malloc(S)
        p1.x = 5

        p2 = lltype.malloc(S)
        p2.x = 5

        p3 = lltype.malloc(S)
        p3.x = 6
        driver = jit.JitDriver(greens = [], reds = ['n', 'x'])
        @jit.elidable_compatible()
        def g(s):
            if s.x == 6:
                raise Exception
            return s.x

        def f(n, x):
            while n > 0:
                driver.can_enter_jit(n=n, x=x)
                driver.jit_merge_point(n=n, x=x)
                try:
                    n -= g(x)
                except:
                    n -= 1

        def main():
            f(100, p1)
            f(100, p2)
            f(100, p3)

        self.meta_interp(main, [])
        self.check_trace_count(3)


    def test_quasi_immutable(self):
        from rpython.rlib.objectmodel import we_are_translated
        class C(object):
            _immutable_fields_ = ['version?']

        class Version(object):
            def __init__(self, cls):
                self.cls = cls
        p1 = C()
        p1.version = Version(p1)
        p1.x = 1
        p2 = C()
        p2.version = Version(p2)
        p2.x = 1
        p3 = C()
        p3.version = Version(p3)
        p3.x = 3

        driver = jit.JitDriver(greens = [], reds = ['n', 'x'])

        class Counter(object):
            pass

        c = Counter()
        c.count = 0
        @jit.elidable_compatible()
        def g(cls, v):
            if we_are_translated():
                c.count += 1
            return cls.x

        def f(n, x):
            res = 0
            while n > 0:
                driver.can_enter_jit(n=n, x=x)
                driver.jit_merge_point(n=n, x=x)
                x = jit.hint(x, promote_compatible=True)
                res = g(x, x.version)
                n -= res
            return res

        def main(x):
            res = f(100, p1)
            assert res == 1
            res = f(100, p2)
            assert res == 1
            res = f(100, p3)
            assert res == 3
            # invalidate p1 or p2
            if x:
                p1.x = 2
                p1.version = Version(p1)
                res = f(100, p1)
                assert res == 2
                p1.x = 1
                p1.version = Version(p1)
            else:
                p2.x = 2
                p2.version = Version(p2)
                res = f(100, p2)
                assert res == 2
                p2.x = 1
                p2.version = Version(p2)
            return c.count
        main(True)
        main(False)

        x = self.meta_interp(main, [True])
        assert x < 30

        x = self.meta_interp(main, [False])
        assert x < 30
        self.check_trace_count(4)


    def test_dont_record_repeated_guard_compatible(self):
        class A:
            pass
        class B(A):
            pass
        @jit.elidable_compatible()
        def extern(x):
            return isinstance(x, A)
        @jit.dont_look_inside
        def pick(n):
            if n:
                x = a
            else:
                x = b
            return x
        a = A()
        b = B()
        def fn(n):
            x = pick(n)
            return extern(x) + extern(x) + extern(x)

        res = self.interp_operations(fn, [1])
        assert res == 3
        self.check_operations_history(guard_compatible=1)


    def test_too_many_bridges(self):
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        p1 = lltype.malloc(S)
        p1.x = 5

        p2 = lltype.malloc(S)
        p2.x = 5

        p3 = lltype.malloc(S)
        p3.x = 6
        driver = jit.JitDriver(greens = [], reds = ['n', 'x'])

        class A(object):
            pass

        c = A()
        c.count = 0
        @jit.elidable_compatible()
        def g(s, ignored):
            c.count += 1
            return s.x

        def f(n, x):
            while n > 0:
                driver.can_enter_jit(n=n, x=x)
                driver.jit_merge_point(n=n, x=x)
                n -= g(x, 7)

        def main():
            g(p1, 9) # make annotator not make argument constant
            f(100, p1)
            f(100, p3) # not compatible, so make a bridge
            f(100, p2) # compatible with loop again, too bad
            return c.count

        x = self.meta_interp(main, [])

        assert x < 30
        # trace, one bridge, a finish bridge
        self.check_trace_count(3)


    def test_order_of_chained_guards(self):
        class Obj(object):
            def __init__(self):
                self.m = Map()
        class Map(object):
            pass

        p1 = Obj()
        p1.m.x = 5
        p1.m.y = 5

        p2 = Obj()
        p2.m.x = 5
        p2.m.y = 5

        p3 = Obj()
        p3.m.x = 5
        p3.m.y = 6
        driver = jit.JitDriver(greens = [], reds = ['n', 'x'])

        class A(object):
            pass

        c = A()
        c.count = 0
        @jit.elidable_compatible()
        def check1(m, ignored):
            c.count += 1
            return m.x

        @jit.elidable_compatible()
        def check2(m, ignored):
            c.count += 1
            return m.y

        def f(n, x):
            while n > 0:
                driver.can_enter_jit(n=n, x=x)
                driver.jit_merge_point(n=n, x=x)
                n -= check1(x.m, 7) + check2(x.m, 7)

        def main():
            check1(p1.m, 9) # make annotator not make argument constant
            f(100, p1)
            f(100, p3) # not compatible, so make a bridge
            f(100, p2) # compatible with loop again, too bad
            return c.count

        x = self.meta_interp(main, [])

        # trace, two bridges, a finish bridge
        self.check_trace_count(3)
        assert x < 30

    def test_merge(self):
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        p1 = lltype.malloc(S)
        p1.x = 1

        p2 = lltype.malloc(S)
        p2.x = 1

        driver = jit.JitDriver(greens = [], reds = ['n', 'x'])

        class A(object):
            pass

        c = A()
        c.count = 0
        @jit.elidable_compatible()
        def g(s, ignored):
            c.count += 1
            return s.x

        def f(n, x):
            while n > 0:
                driver.can_enter_jit(n=n, x=x)
                driver.jit_merge_point(n=n, x=x)
                n -= g(x, "abc")
                if n & 2:
                    n -= 2

        def main():
            g(p1, "def") # make annotator not make argument constant
            f(1000, p1)
            f(1000, p2)
            return c.count

        x = self.meta_interp(main, [])

        assert x < 30
        # trace, two bridges, a finish bridge
        self.check_trace_count(4)

    def test_merge_obj_not_in_failargs(self):
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        p1 = lltype.malloc(S)
        p1.x = 1

        p2 = lltype.malloc(S)
        p2.x = 1

        p3 = lltype.malloc(S)
        p3.x = 2

        p4 = lltype.malloc(S)
        p4.x = 2

        driver = jit.JitDriver(greens = [], reds = ['n'])

        class A(object):
            pass

        c = A()
        c.count = 0
        @jit.elidable_compatible()
        def g(s, ignored):
            c.count += 1
            return s.x

        class B(object):
            pass

        glob_b = B()

        def f(n):
            while n > 0:
                driver.can_enter_jit(n=n)
                driver.jit_merge_point(n=n)
                x = glob_b.x
                n -= g(x, "abc")
                if n & 2:
                    n -= 2

        def main():
            g(p1, "def") # make annotator not make argument constant
            glob_b.x = p1
            f(1000)
            glob_b.x = p2
            f(1000)
            glob_b.x = p3
            f(1000)
            glob_b.x = p4
            f(1000)
            glob_b.x = p1
            f(1000)
            return c.count

        x = self.meta_interp(main, [])

        self.check_trace_count(6)

    def test_merge_switch_object(self):
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        p1 = lltype.malloc(S)
        p1.x = 1

        p2 = lltype.malloc(S)
        p2.x = 1

        driver = jit.JitDriver(greens = [], reds = ['n', 'x', 'y'])

        class A(object):
            pass

        c = A()
        c.count = 0
        @jit.elidable_compatible()
        def g(s, ignored):
            c.count += 1
            return s.x

        def f(n, x, y):
            while n > 0:
                driver.jit_merge_point(n=n, x=x, y=y)
                n -= g(x, "abc")
                if n % 6 == 5:
                    n -= 2
                    x, y = y, x

        def main():
            g(p1, "def") # make annotator not make argument constant
            f(1000, p1, p2)
            f(1000, p2, p1)
            return c.count

        x = self.meta_interp(main, [])

        assert x < 30
        # trace, one bridge, a finish bridge
        self.check_trace_count(3)


    def test_quasi_immutable_merge(self):
        from rpython.rlib.objectmodel import we_are_translated
        class C(object):
            _immutable_fields_ = ['version?']

        class Version(object):
            def __init__(self, cls):
                self.cls = cls
        p1 = C()
        p1.version = Version(p1)
        p1.x = 1
        p2 = C()
        p2.version = Version(p2)
        p2.x = 1
        p3 = C()
        p3.version = Version(p3)
        p3.x = 3

        driver = jit.JitDriver(greens = [], reds = ['n', 'x'])

        class Counter(object):
            pass

        c = Counter()
        c.count = 0
        @jit.elidable_compatible()
        def g(cls, v):
            if we_are_translated():
                c.count += 1
            return cls.x

        def f(n, x):
            res = 0
            while n > 0:
                driver.can_enter_jit(n=n, x=x)
                driver.jit_merge_point(n=n, x=x)
                x = jit.hint(x, promote_compatible=True)
                v = x.version
                res = g(x, x.version)
                n -= res
                if n % 11 == 5:
                    n -= 1
            return res

        def main(x):
            res = f(100, p1)
            assert res == 1
            res = f(100, p2)
            assert res == 1
            res = f(100, p3)
            assert res == 3
            # invalidate p1 or p2
            if x:
                p1.x = 2
                p1.version = Version(p1)
                res = f(100, p1)
                assert res == 2
                p1.x = 1
                p1.version = Version(p1)
            else:
                p2.x = 2
                p2.version = Version(p2)
                res = f(100, p2)
                assert res == 2
                p2.x = 1
                p2.version = Version(p2)
            return c.count
        main(True)
        main(False)

        x = self.meta_interp(main, [True])
        assert x < 30

        x = self.meta_interp(main, [False])
        assert x < 30
        self.check_trace_count(7)

    def test_quasi_immutable_merge_short_preamble(self):
        from rpython.rlib.objectmodel import we_are_translated
        class C(object):
            _immutable_fields_ = ['version?']

        class Version(object):
            def __init__(self, cls):
                self.cls = cls
        p1 = C()
        p1.version = Version(p1)
        p1.x = 1
        p2 = C()
        p2.version = Version(p2)
        p2.x = 1
        p3 = C()
        p3.version = Version(p3)
        p3.x = 3

        driver = jit.JitDriver(greens = [], reds = ['n'])

        class Counter(object):
            pass

        c = Counter()
        c.count = 0
        @jit.elidable_compatible()
        def g(cls, v):
            if we_are_translated():
                c.count += 1
            return cls.x

        class B(object):
            pass

        glob_b = B()

        def f(n, x):
            glob_b.x = x
            res = 0
            while n > 0:
                driver.can_enter_jit(n=n)
                driver.jit_merge_point(n=n)
                x = jit.hint(glob_b.x, promote_compatible=True)
                v = x.version
                res = g(x, v)
                n -= res
                if n % 11 == 5:
                    n -= 1
            return res

        def main(x):
            res = f(100, p1)
            assert res == 1
            res = f(100, p2)
            assert res == 1
            res = f(100, p3)
            assert res == 3
        main(True)
        main(False)

        x = self.meta_interp(main, [True])
        assert x < 70
        x = self.meta_interp(main, [True])
        assert x < 70
        x = self.meta_interp(main, [True])
        assert x < 70
        x = self.meta_interp(main, [True])
        assert x < 70

        x = self.meta_interp(main, [False])
        assert x < 70
        self.check_trace_count(7)
        self.check_resops(call_i=0)


    def test_like_objects(self):
        from rpython.rlib.objectmodel import we_are_translated
        class Map(object):
            _immutable_fields_ = ['version?']

            def __init__(self, num):
                self.num = num
                self.version = Version()
                self.dct = {}
                self.classdct = {}

            def instantiate(self):
                return Obj(self)

            @jit.elidable_compatible(quasi_immut_field_name_for_second_arg='version')
            def lookup_version(self, version, name):
                return self.dct.get(name, -1)

            @jit.elidable_compatible(quasi_immut_field_name_for_second_arg='version')
            def lookup_class(self, version, name):
                return self.classdct.get(name, -1)

        class Version(object):
            pass

        class Obj(object):
            def __init__(self, map):
                self.map = map

            def lookup(self, name):
                map = self.map
                assert isinstance(map, Map)
                map = jit.hint(map, promote_compatible=True)
                result = map.lookup_version(name)
                if result == -1:
                    return map.lookup_class(name)
                return result

        m1 = Map(1)
        m1.dct['a'] = 1
        m1.dct['b'] = 2
        m1.classdct['d'] = 4
        m1.classdct['e'] = 5
        m2 = Map(2)
        m2.dct['a'] = 1
        m2.dct['b'] = 2
        m2.dct['c'] = 5
        m2.classdct['d'] = 4
        m2.classdct['e'] = 5
        m2.classdct['f'] = 5

        m3 = Map(3)
        m3.version = None

        p1 = m1.instantiate()
        p2 = m2.instantiate()
        p3 = m3.instantiate()

        driver = jit.JitDriver(greens = [], reds = ['n', 'res', 'p'])

        def f(n, p):
            res = p.map.num
            while n > 0:
                driver.jit_merge_point(n=n, p=p, res=res)
                version = p.map.version
                if version is not None:
                    res += p.lookup('a')
                    res += p.lookup('c')
                    res += p.lookup('b')
                    res += p.lookup('d')
                    res += p.lookup('e')
                    res += p.lookup('f')
                n -= 1
            return res

        def main(x):
            res = f(100, p1)
            res = f(100, p2)
            res = f(100, p3)
        main(True)
        main(False)

        self.meta_interp(main, [True], backendopt=True)
        self.check_trace_count(2)
        self.check_resops(call_i=0)
