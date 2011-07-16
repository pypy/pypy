import py
import sys
from pypy.rlib import jit
from pypy.jit.metainterp.test.support import LLJitMixin


class TestLLtype(LLJitMixin):
    def test_dont_record_repeated_guard_class(self):
        class A:
            pass
        class B(A):
            pass
        @jit.dont_look_inside
        def extern(n):
            if n == -7:
                return None
            elif n:
                return A()
            else:
                return B()
        def fn(n):
            obj = extern(n)
            return isinstance(obj, B) + isinstance(obj, B) + isinstance(obj, B) + isinstance(obj, B)
        res = self.interp_operations(fn, [0])
        assert res == 4
        self.check_operations_history(guard_class=1, guard_nonnull=1)
        res = self.interp_operations(fn, [1])
        assert not res

    def test_dont_record_guard_class_after_new(self):
        class A:
            pass
        class B(A):
            pass
        def fn(n):
            if n == -7:
                obj = None
            elif n:
                obj = A()
            else:
                obj = B()
            return isinstance(obj, B) + isinstance(obj, B) + isinstance(obj, B) + isinstance(obj, B)
        res = self.interp_operations(fn, [0])
        assert res == 4
        self.check_operations_history(guard_class=0, guard_nonnull=0)
        res = self.interp_operations(fn, [1])
        assert not res

    def test_guard_isnull_nullifies(self):
        class A:
            pass
        a = A()
        a.x = None
        def fn(n):
            if n == -7:
                a.x = ""
            obj = a.x
            res = 0
            if not obj:
                res += 1
            if obj:
                res += 1
            if obj is None:
                res += 1
            if obj is not None:
                res += 1
            return res
        res = self.interp_operations(fn, [0])
        assert res == 2
        self.check_operations_history(guard_isnull=1)

    def test_heap_caching_while_tracing(self):
        class A:
            pass
        a1 = A()
        a2 = A()
        def fn(n):
            if n > 0:
                a = a1
            else:
                a = a2
            a.x = n
            return a.x
        res = self.interp_operations(fn, [7])
        assert res == 7
        self.check_operations_history(getfield_gc=0)
        res = self.interp_operations(fn, [-7])
        assert res == -7
        self.check_operations_history(getfield_gc=0)

        def fn(n, ca, cb):
            a1.x = n
            a2.x = n
            a = a1
            if ca:
                a = a2
            b = a1
            if cb:
                b = a
            return a.x + b.x
        res = self.interp_operations(fn, [7, 0, 1])
        assert res == 7 * 2
        self.check_operations_history(getfield_gc=1)
        res = self.interp_operations(fn, [-7, 1, 1])
        assert res == -7 * 2
        self.check_operations_history(getfield_gc=1)

    def test_heap_caching_while_tracing_invalidation(self):
        class A:
            pass
        a1 = A()
        a2 = A()
        @jit.dont_look_inside
        def f(a):
            a.x = 5
        l = [1]
        def fn(n):
            if n > 0:
                a = a1
            else:
                a = a2
            a.x = n
            x1 = a.x
            f(a)
            x2 = a.x
            l[0] = x2
            return a.x + x1 + x2
        res = self.interp_operations(fn, [7])
        assert res == 5 * 2 + 7
        self.check_operations_history(getfield_gc=1)

    def test_heap_caching_dont_store_same(self):
        class A:
            pass
        a1 = A()
        a2 = A()
        def fn(n):
            if n > 0:
                a = a1
            else:
                a = a2
            a.x = n
            a.x = n
            return a.x
        res = self.interp_operations(fn, [7])
        assert res == 7
        self.check_operations_history(getfield_gc=0, setfield_gc=1)
        res = self.interp_operations(fn, [-7])
        assert res == -7
        self.check_operations_history(getfield_gc=0)

    def test_array_caching(self):
        a1 = [0, 0]
        a2 = [0, 0]
        def fn(n):
            if n > 0:
                a = a1
            else:
                a = a2
            a[0] = n
            x1 = a[0]
            a[n - n] = n + 1
            return a[0] + x1
        res = self.interp_operations(fn, [7])
        assert res == 7 + 7 + 1
        self.check_operations_history(getarrayitem_gc=1)
        res = self.interp_operations(fn, [-7])
        assert res == -7 - 7 + 1
        self.check_operations_history(getarrayitem_gc=1)

        def fn(n, ca, cb):
            a1[0] = n
            a2[0] = n
            a = a1
            if ca:
                a = a2
            b = a1
            if cb:
                b = a
            return a[0] + b[0]
        res = self.interp_operations(fn, [7, 0, 1])
        assert res == 7 * 2
        self.check_operations_history(getarrayitem_gc=1)
        res = self.interp_operations(fn, [-7, 1, 1])
        assert res == -7 * 2
        self.check_operations_history(getarrayitem_gc=1)

    def test_array_caching_while_tracing_invalidation(self):
        a1 = [0, 0]
        a2 = [0, 0]
        @jit.dont_look_inside
        def f(a):
            a[0] = 5
        class A: pass
        l = A()
        def fn(n):
            if n > 0:
                a = a1
            else:
                a = a2
            a[0] = n
            x1 = a[0]
            f(a)
            x2 = a[0]
            l.x = x2
            return a[0] + x1 + x2
        res = self.interp_operations(fn, [7])
        assert res == 5 * 2 + 7
        self.check_operations_history(getarrayitem_gc=1)

    def test_array_and_getfield_interaction(self):
        class A: pass
        a1 = A()
        a2 = A()
        a1.l = a2.l = [0, 0]
        def fn(n):
            if n > 0:
                a = a1
            else:
                a = a2
                a.l = [0, 0]
            a.x = 0
            a.l[a.x] = n
            a.x += 1
            a.l[a.x] = n + 1
            x1 = a.l[a.x]
            a.x -= 1
            x2 = a.l[a.x]
            return x1 + x2
        res = self.interp_operations(fn, [7])
        assert res == 7 * 2 + 1
        self.check_operations_history(setarrayitem_gc=2, setfield_gc=3,
                                      getarrayitem_gc=0, getfield_gc=1)

    def test_promote_changes_heap_cache(self):
        class A: pass
        a1 = A()
        a2 = A()
        a1.l = a2.l = [0, 0]
        a1.x = a2.x = 0
        def fn(n):
            if n > 0:
                a = a1
            else:
                a = a2
                a.l = [0, 0]
            jit.promote(a.x)
            a.l[a.x] = n
            a.x += 1
            a.l[a.x] = n + 1
            x1 = a.l[a.x]
            a.x -= 1
            x2 = a.l[a.x]
            return x1 + x2
        res = self.interp_operations(fn, [7])
        assert res == 7 * 2 + 1
        self.check_operations_history(setarrayitem_gc=2, setfield_gc=2,
                                      getarrayitem_gc=0, getfield_gc=2)

    def test_list_caching(self):
        a1 = [0, 0]
        a2 = [0, 0]
        def fn(n):
            if n > 0:
                a = a1
            else:
                a = a2
                if n < -1000:
                    a.append(5)
            a[0] = n
            x1 = a[0]
            a[n - n] = n + 1
            return a[0] + x1
        res = self.interp_operations(fn, [7])
        assert res == 7 + 7 + 1
        self.check_operations_history(getarrayitem_gc=1,
                getfield_gc=1)
        res = self.interp_operations(fn, [-7])
        assert res == -7 - 7 + 1
        self.check_operations_history(getarrayitem_gc=1,
                getfield_gc=1)

        def fn(n, ca, cb):
            a1[0] = n
            a2[0] = n
            a = a1
            if ca:
                a = a2
                if n < -100:
                    a.append(5)
            b = a1
            if cb:
                b = a
            return a[0] + b[0]
        res = self.interp_operations(fn, [7, 0, 1])
        assert res == 7 * 2
        self.check_operations_history(getarrayitem_gc=1,
                getfield_gc=3)
        res = self.interp_operations(fn, [-7, 1, 1])
        assert res == -7 * 2
        self.check_operations_history(getarrayitem_gc=1,
                getfield_gc=3)
