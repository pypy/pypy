import py
import sys

from pypy.rpython.memory import gcwrapper
from pypy.rpython.memory.test import snippet
from pypy.rpython.test.test_llinterp import get_interpreter
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.rstr import STR
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.objectmodel import compute_unique_id
from pypy.rlib import rgc
from pypy.rlib.rstring import StringBuilder
from pypy.rlib.rarithmetic import LONG_BIT

WORD = LONG_BIT // 8


def stdout_ignore_ll_functions(msg):
    strmsg = str(msg)
    if "evaluating" in strmsg and "ll_" in strmsg:
        return
    print >>sys.stdout, strmsg


class GCTest(object):
    GC_PARAMS = {}
    GC_CAN_MOVE = False
    GC_CAN_MALLOC_NONMOVABLE = True
    GC_CAN_SHRINK_ARRAY = False
    GC_CAN_SHRINK_BIG_ARRAY = False
    BUT_HOW_BIG_IS_A_BIG_STRING = 3*WORD

    def setup_class(cls):
        cls._saved_logstate = py.log._getstate()
        py.log.setconsumer("llinterp", py.log.STDOUT)
        py.log.setconsumer("llinterp frame", stdout_ignore_ll_functions)
        py.log.setconsumer("llinterp operation", None)

    def teardown_class(cls):
        py.log._setstate(cls._saved_logstate)

    def interpret(self, func, values, **kwds):
        interp, graph = get_interpreter(func, values, **kwds)
        gcwrapper.prepare_graphs_and_create_gc(interp, self.GCClass,
                                               self.GC_PARAMS)
        return interp.eval_graph(graph, values)

    def test_llinterp_lists(self):
        #curr = simulator.current_size
        def malloc_a_lot():
            i = 0
            while i < 10:
                i += 1
                a = [1] * 10
                j = 0
                while j < 20:
                    j += 1
                    a.append(j)
        res = self.interpret(malloc_a_lot, [])
        #assert simulator.current_size - curr < 16000 * INT_SIZE / 4
        #print "size before: %s, size after %s" % (curr, simulator.current_size)

    def test_llinterp_tuples(self):
        #curr = simulator.current_size
        def malloc_a_lot():
            i = 0
            while i < 10:
                i += 1
                a = (1, 2, i)
                b = [a] * 10
                j = 0
                while j < 20:
                    j += 1
                    b.append((1, j, i))
        res = self.interpret(malloc_a_lot, [])
        #assert simulator.current_size - curr < 16000 * INT_SIZE / 4
        #print "size before: %s, size after %s" % (curr, simulator.current_size)

    def test_global_list(self):
        lst = []
        def append_to_list(i, j):
            lst.append([i] * 50)
            return lst[j][0]
        res = self.interpret(append_to_list, [0, 0])
        assert res == 0
        for i in range(1, 15):
            res = self.interpret(append_to_list, [i, i - 1])
            assert res == i - 1 # crashes if constants are not considered roots
            
    def test_string_concatenation(self):
        #curr = simulator.current_size
        def concat(j):
            lst = []
            for i in range(j):
                lst.append(str(i))
            return len("".join(lst))
        res = self.interpret(concat, [100])
        assert res == concat(100)
        #assert simulator.current_size - curr < 16000 * INT_SIZE / 4


    def test_collect(self):
        #curr = simulator.current_size
        def concat(j):
            lst = []
            for i in range(j):
                lst.append(str(i))
            result = len("".join(lst))
            if we_are_translated():
                # can't call llop.gc__collect directly
                llop.gc__collect(lltype.Void)
            return result
        res = self.interpret(concat, [100])
        assert res == concat(100)
        #assert simulator.current_size - curr < 16000 * INT_SIZE / 4

    def test_collect_0(self):
        #curr = simulator.current_size
        def concat(j):
            lst = []
            for i in range(j):
                lst.append(str(i))
            result = len("".join(lst))
            if we_are_translated():
                # can't call llop.gc__collect directly
                llop.gc__collect(lltype.Void, 0)
            return result
        res = self.interpret(concat, [100])
        assert res == concat(100)
        #assert simulator.current_size - curr < 16000 * INT_SIZE / 4

    def test_lightweight_finalizer(self):
        T = lltype.Struct('T', ('x', lltype.Signed))
        
        @rgc.owns_raw_memory('p')
        class AClass(object):
            p = lltype.nullptr(T)

            def __init__(self, arg):
                if arg:
                    self.p = lltype.malloc(T, flavor='raw')

        def f():
            for i in range(3):
                AClass(3)
                AClass(0)
            llop.gc__collect(lltype.Void)
            # assert did not crash with malloc mismatch, ie those things
            # has been freed

        self.interpret(f, [])
        
    def test_finalizer(self):
        class B(object):
            pass
        b = B()
        b.nextid = 0
        b.num_deleted = 0
        class A(object):
            def __init__(self):
                self.id = b.nextid
                b.nextid += 1
            def __del__(self):
                b.num_deleted += 1
        def f(x):
            a = A()
            i = 0
            while i < x:
                i += 1
                a = A()
            llop.gc__collect(lltype.Void)
            llop.gc__collect(lltype.Void)
            return b.num_deleted
        res = self.interpret(f, [5])
        assert res == 6

    def test_finalizer_calls_malloc(self):
        class B(object):
            pass
        b = B()
        b.nextid = 0
        b.num_deleted = 0
        class A(object):
            def __init__(self):
                self.id = b.nextid
                b.nextid += 1
            def __del__(self):
                b.num_deleted += 1
                C()
        class C(A):
            def __del__(self):
                b.num_deleted += 1
        def f(x):
            a = A()
            i = 0
            while i < x:
                i += 1
                a = A()
            llop.gc__collect(lltype.Void)
            llop.gc__collect(lltype.Void)
            return b.num_deleted
        res = self.interpret(f, [5])
        assert res == 12

    def test_finalizer_calls_collect(self):
        class B(object):
            pass
        b = B()
        b.nextid = 0
        b.num_deleted = 0
        class A(object):
            def __init__(self):
                self.id = b.nextid
                b.nextid += 1
            def __del__(self):
                b.num_deleted += 1
                llop.gc__collect(lltype.Void)
        def f(x):
            a = A()
            i = 0
            while i < x:
                i += 1
                a = A()
            llop.gc__collect(lltype.Void)
            llop.gc__collect(lltype.Void)
            return b.num_deleted
        res = self.interpret(f, [5])
        assert res == 6

    def test_finalizer_resurrects(self):
        class B(object):
            pass
        b = B()
        b.nextid = 0
        b.num_deleted = 0
        class A(object):
            def __init__(self):
                self.id = b.nextid
                b.nextid += 1
            def __del__(self):
                b.num_deleted += 1
                b.a = self
        def f(x):
            a = A()
            i = 0
            while i < x:
                i += 1
                a = A()
            llop.gc__collect(lltype.Void)
            llop.gc__collect(lltype.Void)
            aid = b.a.id
            b.a = None
            # check that __del__ is not called again
            llop.gc__collect(lltype.Void)
            llop.gc__collect(lltype.Void)
            return b.num_deleted * 10 + aid + 100 * (b.a is None)
        res = self.interpret(f, [5])
        assert 160 <= res <= 165

    def test_custom_trace(self):
        from pypy.rpython.annlowlevel import llhelper
        from pypy.rpython.lltypesystem import llmemory
        from pypy.rpython.lltypesystem.llarena import ArenaError
        #
        S = lltype.GcStruct('S', ('x', llmemory.Address),
                                 ('y', llmemory.Address), rtti=True)
        T = lltype.GcStruct('T', ('z', lltype.Signed))
        offset_of_x = llmemory.offsetof(S, 'x')
        def customtrace(obj, prev):
            if not prev:
                return obj + offset_of_x
            else:
                return llmemory.NULL
        CUSTOMTRACEFUNC = lltype.FuncType([llmemory.Address, llmemory.Address],
                                          llmemory.Address)
        customtraceptr = llhelper(lltype.Ptr(CUSTOMTRACEFUNC), customtrace)
        lltype.attachRuntimeTypeInfo(S, customtraceptr=customtraceptr)
        #
        for attrname in ['x', 'y']:
            def setup():
                s1 = lltype.malloc(S)
                tx = lltype.malloc(T)
                tx.z = 42
                ty = lltype.malloc(T)
                s1.x = llmemory.cast_ptr_to_adr(tx)
                s1.y = llmemory.cast_ptr_to_adr(ty)
                return s1
            def f():
                s1 = setup()
                llop.gc__collect(lltype.Void)
                return llmemory.cast_adr_to_ptr(getattr(s1, attrname),
                                                lltype.Ptr(T))
            if attrname == 'x':
                res = self.interpret(f, [])
                assert res.z == 42
            else:
                py.test.raises((RuntimeError, ArenaError),
                               self.interpret, f, [])

    def test_weakref(self):
        import weakref, gc
        class A(object):
            pass
        def g():
            a = A()
            return weakref.ref(a)
        def f():
            a = A()
            ref = weakref.ref(a)
            result = ref() is a
            ref = g()
            llop.gc__collect(lltype.Void)
            result = result and (ref() is None)
            # check that a further collection is fine
            llop.gc__collect(lltype.Void)
            result = result and (ref() is None)
            return result
        res = self.interpret(f, [])
        assert res

    def test_weakref_to_object_with_finalizer(self):
        import weakref, gc
        class A(object):
            count = 0
        a = A()
        class B(object):
            def __del__(self):
                a.count += 1
        def g():
            b = B()
            return weakref.ref(b)
        def f():
            ref = g()
            llop.gc__collect(lltype.Void)
            llop.gc__collect(lltype.Void)
            result = a.count == 1 and (ref() is None)
            return result
        res = self.interpret(f, [])
        assert res

    def test_bug_1(self):
        import weakref
        class B(object):
            pass
        def g():
            b = B()
            llop.gc__collect(lltype.Void)    # force 'b' to be old
            ref = weakref.ref(B())
            b.ref = ref
            return ref
        def f():
            ref = g()
            llop.gc__collect(lltype.Void)
            llop.gc__collect(lltype.Void)
            result = (ref() is None)
            return result
        res = self.interpret(f, [])
        assert res

    def test_cycle_with_weakref_and_del(self):
        import weakref, gc
        class A(object):
            count = 0
        a = A()
        class B(object):
            def __del__(self):
                # when __del__ is called, the weakref to c should be dead
                if self.ref() is None:
                    a.count += 10  # ok
                else:
                    a.count = 666  # not ok
        class C(object):
            pass
        def g():
            c = C()
            c.b = B()
            ref = weakref.ref(c)
            c.b.ref = ref
            return ref
        def f():
            ref = g()
            llop.gc__collect(lltype.Void)
            llop.gc__collect(lltype.Void)
            result = a.count + (ref() is None)
            return result
        res = self.interpret(f, [])
        assert res == 11

    def test_weakref_to_object_with_finalizer_ordering(self):
        import weakref, gc
        class A(object):
            count = 0
        a = A()
        class B(object):
            def __del__(self):
                # when __del__ is called, the weakref to myself is still valid
                # in RPython (at least with most GCs; this test might be
                # skipped for specific GCs)
                if self.ref() is self:
                    a.count += 10  # ok
                else:
                    a.count = 666  # not ok
        def g():
            b = B()
            ref = weakref.ref(b)
            b.ref = ref
            return ref
        def f():
            ref = g()
            llop.gc__collect(lltype.Void)
            llop.gc__collect(lltype.Void)
            result = a.count + (ref() is None)
            return result
        res = self.interpret(f, [])
        assert res == 11

    def test_weakref_bug_1(self):
        import weakref
        class A(object):
            pass
        class B(object):
            def __del__(self):
                self.wref().x += 1
        def g(a):
            b = B()
            b.wref = weakref.ref(a)
            # the only way to reach this weakref is via B, which is an
            # object with finalizer (but the weakref itself points to
            # a, which does not go away but will move during the next
            # gc.collect)
        def f():
            a = A()
            a.x = 10
            g(a)
            llop.gc__collect(lltype.Void)
            return a.x
        res = self.interpret(f, [])
        assert res == 11

    def test_id(self):
        class A(object):
            pass
        a1 = A()
        def f():
            a2 = A()
            a3 = A()
            id1 = compute_unique_id(a1)
            id2 = compute_unique_id(a2)
            id3 = compute_unique_id(a3)
            llop.gc__collect(lltype.Void)
            error = 0
            if id1 != compute_unique_id(a1): error += 1
            if id2 != compute_unique_id(a2): error += 2
            if id3 != compute_unique_id(a3): error += 4
            return error
        res = self.interpret(f, [])
        assert res == 0

    def test_finalizer_calls_malloc_during_minor_collect(self):
        # originally a GenerationGC test, this has also found bugs in other GCs
        class B(object):
            pass
        b = B()
        b.nextid = 0
        b.num_deleted = 0
        b.all = []
        class A(object):
            def __init__(self):
                self.id = b.nextid
                b.nextid += 1
            def __del__(self):
                b.num_deleted += 1
                b.all.append(D(b.num_deleted))
        class D(object):
            # make a big object that does not use malloc_varsize
            def __init__(self, x):
                self.x00 = self.x01 = self.x02 = self.x03 = self.x04 = x
                self.x10 = self.x11 = self.x12 = self.x13 = self.x14 = x
                self.x20 = self.x21 = self.x22 = self.x23 = self.x24 = x
        def f(x):
            i = 0
            all = [None] * x
            a = A()
            while i < x:
                d = D(i)
                all[i] = d
                i += 1
            return b.num_deleted + len(all)
        res = self.interpret(f, [500])
        assert res == 1 + 500


    def test_collect_during_collect(self):
        class B(object):
            pass
        b = B()
        b.nextid = 1
        b.num_deleted = 0
        b.num_deleted_c = 0
        class A(object):
            def __init__(self):
                self.id = b.nextid
                b.nextid += 1
            def __del__(self):
                llop.gc__collect(lltype.Void)
                b.num_deleted += 1
                C()
                C()
        class C(A):
            def __del__(self):
                b.num_deleted += 1
                b.num_deleted_c += 1
        def f(x, y):
            persistent_a1 = A()
            persistent_a2 = A()
            i = 0
            while i < x:
                i += 1
                a = A()
            persistent_a3 = A()
            persistent_a4 = A()
            llop.gc__collect(lltype.Void)
            llop.gc__collect(lltype.Void)
            b.bla = persistent_a1.id + persistent_a2.id + persistent_a3.id + persistent_a4.id
            print b.num_deleted_c
            return b.num_deleted
        res = self.interpret(f, [4, 42])
        assert res == 12

    def test_print_leak(self):
        def f(n):
            for i in range(n):
                print i
            return 42
        res = self.interpret(f, [10])
        assert res == 42

    def test_weakref_across_minor_collection(self):
        import weakref
        class A:
            pass
        def f(x):
            a = A()
            a.foo = x
            ref = weakref.ref(a)
            all = [None] * x
            i = 0
            while i < x:
                all[i] = [i] * i
                i += 1
            assert ref() is a
            llop.gc__collect(lltype.Void)
            assert ref() is a
            return a.foo + len(all)
        res = self.interpret(f, [20])  # for GenerationGC, enough for a minor collection
        assert res == 20 + 20

    def test_young_weakref_to_old_object(self):
        import weakref
        class A:
            pass
        def f(x):
            a = A()
            llop.gc__collect(lltype.Void)
            # 'a' is old, 'ref' is young
            ref = weakref.ref(a)
            # now trigger a minor collection
            all = [None] * x
            i = 0
            while i < x:
                all[i] = [i] * i
                i += 1
            # now 'a' is old, but 'ref' did not move
            assert ref() is a
            llop.gc__collect(lltype.Void)
            # now both 'a' and 'ref' have moved
            return ref() is a
        res = self.interpret(f, [20])  # for GenerationGC, enough for a minor collection
        assert res == True

    def test_many_weakrefs(self):
        # test for the case where allocating the weakref itself triggers
        # a collection
        import weakref
        class A:
            pass
        def f(x):
            a = A()
            i = 0
            while i < x:
                ref = weakref.ref(a)
                assert ref() is a
                i += 1
        self.interpret(f, [1100])

    def test_nongc_static_root(self):
        from pypy.rpython.lltypesystem import lltype
        T1 = lltype.GcStruct("C", ('x', lltype.Signed))
        T2 = lltype.Struct("C", ('p', lltype.Ptr(T1)))
        static = lltype.malloc(T2, immortal=True)
        def f():
            t1 = lltype.malloc(T1)
            t1.x = 42
            static.p = t1
            llop.gc__collect(lltype.Void)
            return static.p.x
        res = self.interpret(f, [])
        assert res == 42

    def test_can_move(self):
        TP = lltype.GcArray(lltype.Float)
        def func():
            return rgc.can_move(lltype.malloc(TP, 1))
        assert self.interpret(func, []) == self.GC_CAN_MOVE

    
    def test_malloc_nonmovable(self):
        TP = lltype.GcArray(lltype.Char)
        def func():
            a = rgc.malloc_nonmovable(TP, 3)
            if a:
                assert not rgc.can_move(a)
                return 1
            return 0

        assert self.interpret(func, []) == int(self.GC_CAN_MALLOC_NONMOVABLE)

    def test_malloc_nonmovable_fixsize(self):
        S = lltype.GcStruct('S', ('x', lltype.Float))
        TP = lltype.GcStruct('T', ('s', lltype.Ptr(S)))
        def func():
            try:
                a = rgc.malloc_nonmovable(TP)
                rgc.collect()
                if a:
                    assert not rgc.can_move(a)
                    return 1
                return 0
            except Exception, e:
                return 2

        assert self.interpret(func, []) == int(self.GC_CAN_MALLOC_NONMOVABLE)

    def test_shrink_array(self):
        from pypy.rpython.lltypesystem.rstr import STR

        def f(n, m, gc_can_shrink_array):
            ptr = lltype.malloc(STR, n)
            ptr.hash = 0x62
            ptr.chars[0] = 'A'
            ptr.chars[1] = 'B'
            ptr.chars[2] = 'C'
            ptr2 = rgc.ll_shrink_array(ptr, 2)
            assert (ptr == ptr2) == gc_can_shrink_array
            rgc.collect()
            return ( ord(ptr2.chars[0])       +
                    (ord(ptr2.chars[1]) << 8) +
                    (len(ptr2.chars)   << 16) +
                    (ptr2.hash         << 24))

        flag = self.GC_CAN_SHRINK_ARRAY
        assert self.interpret(f, [3, 0, flag]) == 0x62024241
        # with larger numbers, it gets allocated outside the semispace
        # with some GCs.
        flag = self.GC_CAN_SHRINK_BIG_ARRAY
        bigsize = self.BUT_HOW_BIG_IS_A_BIG_STRING
        assert self.interpret(f, [bigsize, 0, flag]) == 0x62024241

    def test_tagged_simple(self):
        from pypy.rlib.objectmodel import UnboxedValue

        class Unrelated(object):
            pass

        u = Unrelated()
        u.x = UnboxedObject(47)
        def fn(n):
            rgc.collect() # check that a prebuilt tagged pointer doesn't explode
            if n > 0:
                x = BoxedObject(n)
            else:
                x = UnboxedObject(n)
            u.x = x # invoke write barrier
            rgc.collect()
            return x.meth(100)
        res = self.interpret(fn, [1000], taggedpointers=True)
        assert res == 1102
        res = self.interpret(fn, [-1000], taggedpointers=True)
        assert res == -897

    def test_tagged_prebuilt(self):

        class F:
            pass

        f = F()
        f.l = [UnboxedObject(10)]
        def fn(n):
            if n > 0:
                x = BoxedObject(n)
            else:
                x = UnboxedObject(n)
            f.l.append(x)
            rgc.collect()
            return f.l[-1].meth(100)
        res = self.interpret(fn, [1000], taggedpointers=True)
        assert res == 1102
        res = self.interpret(fn, [-1000], taggedpointers=True)
        assert res == -897

    def test_tagged_id(self):
        from pypy.rlib.objectmodel import UnboxedValue, compute_unique_id

        class Unrelated(object):
            pass

        u = Unrelated()
        u.x = UnboxedObject(0)
        def fn(n):
            id_prebuilt1 = compute_unique_id(u.x)
            if n > 0:
                x = BoxedObject(n)
            else:
                x = UnboxedObject(n)
            id_x1 = compute_unique_id(x)
            rgc.collect() # check that a prebuilt tagged pointer doesn't explode
            id_prebuilt2 = compute_unique_id(u.x)
            id_x2 = compute_unique_id(x)
            print u.x, id_prebuilt1, id_prebuilt2
            print x, id_x1, id_x2
            return ((id_x1 == id_x2) * 1 +
                    (id_prebuilt1 == id_prebuilt2) * 10 +
                    (id_x1 != id_prebuilt1) * 100)
        res = self.interpret(fn, [1000], taggedpointers=True)
        assert res == 111
        res = self.interpret(fn, [-1000], taggedpointers=True)
        assert res == 111

    def test_writebarrier_before_copy(self):
        S = lltype.GcStruct('S', ('x', lltype.Char))
        TP = lltype.GcArray(lltype.Ptr(S))
        def fn():
            l = lltype.malloc(TP, 100)
            l2 = lltype.malloc(TP, 100)
            for i in range(100):
                l[i] = lltype.malloc(S)
            rgc.ll_arraycopy(l, l2, 50, 0, 50)
            x = []
            # force minor collect
            t = (1, lltype.malloc(S))
            for i in range(20):
                x.append(t)
            for i in range(50):
                assert l2[i] == l[50 + i]
            return 0

        self.interpret(fn, [])

    def test_stringbuilder(self):
        def fn():
            s = StringBuilder(4)
            s.append("abcd")
            s.append("defg")
            s.append("rty")
            s.append_multiple_char('y', 1000)
            rgc.collect()
            s.append_multiple_char('y', 1000)
            res = s.build()[1000]
            rgc.collect()
            return ord(res)
        res = self.interpret(fn, [])
        assert res == ord('y')

from pypy.rlib.objectmodel import UnboxedValue

class TaggedBase(object):
    __slots__ = ()
    def meth(self, x):
        raise NotImplementedError

class BoxedObject(TaggedBase):
    attrvalue = 66
    def __init__(self, normalint):
        self.normalint = normalint
    def meth(self, x):
        return self.normalint + x + 2

class UnboxedObject(TaggedBase, UnboxedValue):
    __slots__ = 'smallint'
    def meth(self, x):
        return self.smallint + x + 3


class TestMarkSweepGC(GCTest):
    from pypy.rpython.memory.gc.marksweep import MarkSweepGC as GCClass

    def test_weakref_to_object_with_finalizer_ordering(self):
        py.test.skip("Does not work")

class TestSemiSpaceGC(GCTest, snippet.SemiSpaceGCTests):
    from pypy.rpython.memory.gc.semispace import SemiSpaceGC as GCClass
    GC_CAN_MOVE = True
    GC_CAN_MALLOC_NONMOVABLE = False
    GC_CAN_SHRINK_ARRAY = True
    GC_CAN_SHRINK_BIG_ARRAY = True

class TestGrowingSemiSpaceGC(TestSemiSpaceGC):
    GC_PARAMS = {'space_size': 16*WORD}

class TestGenerationalGC(TestSemiSpaceGC):
    from pypy.rpython.memory.gc.generation import GenerationGC as GCClass

class TestMarkCompactGC(TestSemiSpaceGC):
    from pypy.rpython.memory.gc.markcompact import MarkCompactGC as GCClass
    GC_PARAMS = {'space_size': 65536+16384}
    GC_CAN_SHRINK_ARRAY = False
    GC_CAN_SHRINK_BIG_ARRAY = False

    def test_finalizer_order(self):
        py.test.skip("Not implemented yet")

class TestHybridGC(TestGenerationalGC):
    from pypy.rpython.memory.gc.hybrid import HybridGC as GCClass
    GC_CAN_MALLOC_NONMOVABLE = True
    GC_CAN_SHRINK_BIG_ARRAY = False

    def test_ref_from_rawmalloced_to_regular(self):
        import gc
        def concat(j):
            lst = []
            for i in range(j):
                lst.append(str(i))
            gc.collect()
            return len("".join(lst))
        res = self.interpret(concat, [100])
        assert res == concat(100)

    def test_longliving_weakref(self):
        # test for the case where a weakref points to a very old object
        # that was made non-movable after several collections
        import gc, weakref
        class A:
            pass
        def step1(x):
            a = A()
            a.x = 42
            ref = weakref.ref(a)
            i = 0
            while i < x:
                gc.collect()
                i += 1
            assert ref() is a
            assert ref().x == 42
            return ref
        def step2(ref):
            gc.collect()       # 'a' is freed here
            assert ref() is None
        def f(x):
            ref = step1(x)
            step2(ref)
        self.interpret(f, [10])

    def test_longliving_object_with_finalizer(self):
        class B(object):
            pass
        b = B()
        b.nextid = 0
        b.num_deleted = 0
        class A(object):
            def __init__(self):
                self.id = b.nextid
                b.nextid += 1
            def __del__(self):
                b.num_deleted += 1
        def f(x):
            a = A()
            i = 0
            while i < x:
                i += 1
                a = A()
                llop.gc__collect(lltype.Void)
            llop.gc__collect(lltype.Void)
            llop.gc__collect(lltype.Void)
            return b.num_deleted
        res = self.interpret(f, [15])
        assert res == 16

    def test_malloc_nonmovable_fixsize(self):
        py.test.skip("Not supported")

class TestHybridGCSmallHeap(GCTest):
    from pypy.rpython.memory.gc.hybrid import HybridGC as GCClass
    GC_CAN_MOVE = False # with this size of heap, stuff gets allocated
                        # in 3rd gen.
    GC_CAN_MALLOC_NONMOVABLE = True
    GC_PARAMS = {'space_size': 48*WORD,
                 'min_nursery_size': 12*WORD,
                 'nursery_size': 12*WORD,
                 'large_object': 3*WORD,
                 'large_object_gcptrs': 3*WORD,
                 'generation3_collect_threshold': 5,
                 }

    def test_gen3_to_gen2_refs(self):
        class A(object):
            def __init__(self):
                self.x1 = -1
        def f(x):
            loop = A()
            loop.next = loop
            loop.prev = loop
            i = 0
            while i < x:
                i += 1
                a1 = A()
                a1.x1 = i
                a2 = A()
                a2.x1 = i + 1000
                a1.prev = loop.prev
                a1.prev.next = a1
                a1.next = loop
                loop.prev = a1
                a2.prev = loop
                a2.next = loop.next
                a2.next.prev = a2
                loop.next = a2
            i = 0
            a = loop
            while True:
                a = a.next
                i += 1
                if a is loop:
                    return i
        res = self.interpret(f, [200])
        assert res == 401

    def test_malloc_nonmovable_fixsize(self):
        py.test.skip("Not supported")


class TestMiniMarkGC(TestSemiSpaceGC):
    from pypy.rpython.memory.gc.minimark import MiniMarkGC as GCClass
    GC_CAN_SHRINK_BIG_ARRAY = False
    GC_CAN_MALLOC_NONMOVABLE = True
    BUT_HOW_BIG_IS_A_BIG_STRING = 11*WORD

class TestMiniMarkGCCardMarking(TestMiniMarkGC):
    GC_PARAMS = {'card_page_indices': 4}
