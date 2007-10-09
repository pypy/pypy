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

    def setup_class(cls):
        cls._saved_logstate = py.log._getstate()
        py.log.setconsumer("llinterp", py.log.STDOUT)
        py.log.setconsumer("llinterp frame", stdout_ignore_ll_functions)
        py.log.setconsumer("llinterp operation", None)

    def teardown_class(cls):
        py.log._setstate(cls._saved_logstate)

    def interpret(self, func, values, **kwds):
        interp, graph = get_interpreter(func, values, **kwds)
        gcwrapper.prepare_graphs_and_create_gc(interp, self.GCClass)
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


class TestMarkSweepGC(GCTest):
    from pypy.rpython.memory.gc import MarkSweepGC as GCClass

class TestSemiSpaceGC(GCTest):
    from pypy.rpython.memory.gc import SemiSpaceGC as GCClass
    def test_finalizer(self):
        py.test.skip("implement me")

class TestDeferredRefcountingGC(GCTest):
    from pypy.rpython.memory.gc import DeferredRefcountingGC as GCClass
    def setup_class(cls):
        py.test.skip("DeferredRefcounting is unmaintained")
