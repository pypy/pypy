import py
import sys

#from pypy.rpython.memory.support import INT_SIZE
from pypy.rpython.memory import gcwrapper
from pypy.rpython.test.test_llinterp import get_interpreter
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.objectmodel import we_are_translated


def stdout_ignore_ll_functions(msg):
    strmsg = str(msg)
    if "evaluating" in strmsg and "ll_" in strmsg:
        return
    print >>sys.stdout, strmsg


class GCTest(object):
    GC_PARAMS = {}

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

    def test_id(self):
        py.test.skip("the MovingGCBase.id() logic can't be directly run")
        # XXX ^^^ the problem is that the MovingGCBase instance holds
        # references to GC objects - a list of weakrefs and a dict - and
        # there is no way we can return these from get_roots_from_llinterp().
        class A(object):
            pass
        a1 = A()
        def f():
            a2 = A()
            a3 = A()
            id1 = id(a1)
            id2 = id(a2)
            id3 = id(a3)
            llop.gc__collect(lltype.Void)
            error = 0
            if id1 != id(a1): error += 1
            if id2 != id(a2): error += 2
            if id3 != id(a3): error += 4
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


class TestMarkSweepGC(GCTest):
    from pypy.rpython.memory.gc.marksweep import MarkSweepGC as GCClass

class TestSemiSpaceGC(GCTest):
    from pypy.rpython.memory.gc.semispace import SemiSpaceGC as GCClass

class TestGrowingSemiSpaceGC(TestSemiSpaceGC):
    GC_PARAMS = {'space_size': 64}

class TestGenerationalGC(GCTest):
    from pypy.rpython.memory.gc.generation import GenerationGC as GCClass
