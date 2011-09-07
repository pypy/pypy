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

    def test_promote_changes_array_cache(self):
        a1 = [0, 0]
        a2 = [0, 0]
        def fn(n):
            if n > 0:
                a = a1
            else:
                a = a2
            a[0] = n
            jit.hint(n, promote=True)
            x1 = a[0]
            jit.hint(x1, promote=True)
            a[n - n] = n + 1
            return a[0] + x1
        res = self.interp_operations(fn, [7])
        assert res == 7 + 7 + 1
        self.check_operations_history(getarrayitem_gc=0, guard_value=1)
        res = self.interp_operations(fn, [-7])
        assert res == -7 - 7 + 1
        self.check_operations_history(getarrayitem_gc=0, guard_value=1)


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

    def test_list_caching_negative(self):
        def fn(n):
            a = [0] * n
            if n > 1000:
                a.append(0)
            a[-1] = n
            x1 = a[-1]
            a[n - n - 1] = n + 1
            return a[-1] + x1
        res = self.interp_operations(fn, [7])
        assert res == 7 + 7 + 1
        self.check_operations_history(setarrayitem_gc=2,
                setfield_gc=2)

    def test_virtualizable_with_array_heap_cache(self):
        myjitdriver = jit.JitDriver(greens = [], reds = ['n', 'x', 'i', 'frame'],
                                    virtualizables = ['frame'])

        class Frame(object):
            _virtualizable2_ = ['l[*]', 's']

            def __init__(self, a, s):
                self = jit.hint(self, access_directly=True, fresh_virtualizable=True)
                self.l = [0] * (4 + a)
                self.s = s

        def f(n, a, i):
            frame = Frame(a, 0)
            frame.l[0] = a
            frame.l[1] = a + 1
            frame.l[2] = a + 2
            frame.l[3] = a + 3
            if not i:
                return frame.l[0] + len(frame.l)
            x = 0
            while n > 0:
                myjitdriver.can_enter_jit(frame=frame, n=n, x=x, i=i)
                myjitdriver.jit_merge_point(frame=frame, n=n, x=x, i=i)
                frame.s = jit.promote(frame.s)
                n -= 1
                s = frame.s
                assert s >= 0
                x += frame.l[s]
                frame.s += 1
                s = frame.s
                assert s >= 0
                x += frame.l[s]
                x += len(frame.l)
                x += f(n, n, 0)
                frame.s -= 1
            return x

        res = self.meta_interp(f, [10, 1, 1], listops=True)
        assert res == f(10, 1, 1)
        self.check_history(getarrayitem_gc=0, getfield_gc=0)

    def test_heap_caching_array_pure(self):
        class A(object):
            pass
        p1 = A()
        p2 = A()
        def fn(n):
            if n >= 0:
                a = (n, n + 1)
                p = p1
            else:
                a = (n + 1, n)
                p = p2
            p.x = a

            return p.x[0] + p.x[1]
        res = self.interp_operations(fn, [7])
        assert res == 7 + 7 + 1
        self.check_operations_history(getfield_gc=0, getfield_gc_pure=0)
        res = self.interp_operations(fn, [-7])
        assert res == -7 - 7 + 1
        self.check_operations_history(getfield_gc=0, getfield_gc_pure=0)

    def test_heap_caching_and_elidable_function(self):
        class A:
            pass
        class B: pass
        a1 = A()
        a1.y = 6
        a2 = A()
        a2.y = 13
        @jit.elidable
        def f(b):
            return b + 1
        def fn(n):
            if n > 0:
                a = a1
            else:
                a = A()
            a.x = n
            z = f(6)
            return z + a.x
        res = self.interp_operations(fn, [7])
        assert res == 7 + 7
        self.check_operations_history(getfield_gc=0)
        res = self.interp_operations(fn, [-7])
        assert res == -7 + 7
        self.check_operations_history(getfield_gc=0)
        return


    def test_heap_caching_multiple_objects(self):
        class Gbl(object):
            pass
        g = Gbl()
        class A(object):
            pass
        def fn(n):
            a1 = A()
            g.a = a1
            a1.x = n
            a2 = A()
            g.a = a2
            a2.x = n - 1
            return a1.x + a2.x + a1.x + a2.x
        res = self.interp_operations(fn, [7])
        assert res == 2 * 7 + 2 * 6
        self.check_operations_history(getfield_gc=0)
        res = self.interp_operations(fn, [-7])
        assert res == 2 * -7 + 2 * -8
        self.check_operations_history(getfield_gc=0)

    def test_heap_caching_multiple_tuples(self):
        class Gbl(object):
            pass
        g = Gbl()
        def gn(a1, a2):
            return a1[0] + a2[0]
        def fn(n):
            a1 = (n, )
            g.a = a1
            a2 = (n - 1, )
            g.a = a2
            jit.promote(n)
            return a1[0] + a2[0] + gn(a1, a2)
        res = self.interp_operations(fn, [7])
        assert res == 2 * 7 + 2 * 6
        self.check_operations_history(getfield_gc_pure=0)
        res = self.interp_operations(fn, [-7])
        assert res == 2 * -7 + 2 * -8
        self.check_operations_history(getfield_gc_pure=0)

    def test_heap_caching_multiple_arrays(self):
        class Gbl(object):
            pass
        g = Gbl()
        def fn(n):
            a1 = [n, n, n]
            g.a = a1
            a1[0] = n
            a2 = [n, n, n]
            g.a = a2
            a2[0] = n - 1
            return a1[0] + a2[0] + a1[0] + a2[0]
        res = self.interp_operations(fn, [7])
        assert res == 2 * 7 + 2 * 6
        self.check_operations_history(getarrayitem_gc=0)
        res = self.interp_operations(fn, [-7])
        assert res == 2 * -7 + 2 * -8
        self.check_operations_history(getarrayitem_gc=0)

    def test_heap_caching_multiple_arrays_getarrayitem(self):
        class Gbl(object):
            pass
        g = Gbl()
        g.a1 = [7, 8, 9]
        g.a2 = [8, 9, 10, 11]

        def fn(i):
            if i < 0:
                g.a1 = [7, 8, 9]
                g.a2 = [7, 8, 9, 10]
            jit.promote(i)
            a1 = g.a1
            a1[i + 1] = 15 # make lists mutable
            a2 = g.a2
            a2[i + 1] = 19
            return a1[i] + a2[i] + a1[i] + a2[i]
        res = self.interp_operations(fn, [0])
        assert res == 2 * 7 + 2 * 8
        self.check_operations_history(getarrayitem_gc=2)

    def test_length_caching(self):
        class Gbl(object):
            pass
        g = Gbl()
        g.a = [0] * 7
        def fn(n):
            a = g.a
            res = len(a) + len(a)
            a1 = [0] * n
            g.a = a1
            return len(a1) + res
        res = self.interp_operations(fn, [7])
        assert res == 7 * 3
        self.check_operations_history(arraylen_gc=1)
