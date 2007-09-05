import py
import sys

from pypy.annotation import model as annmodel
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.rpython.rtyper import RPythonTyper
from pypy.rpython.memory.gc import GCError, MarkSweepGC, SemiSpaceGC
from pypy.rpython.memory.gc import DeferredRefcountingGC, DummyGC
from pypy.rpython.memory.support import INT_SIZE
from pypy.rpython.memory import support
from pypy.rpython.memory.lladdress import raw_malloc, raw_free, NULL
from pypy.rpython.memory.simulator import MemorySimulatorError
from pypy.rpython.memory import gclltype
from pypy.rpython.memory.test.test_llinterpsim import interpret
from pypy.rpython.memory.lladdress import simulator
from pypy.rlib.objectmodel import free_non_gc_object

def setup_module(mod):
    def stdout_ignore_ll_functions(msg):
        strmsg = str(msg)
        if "evaluating" in strmsg and "ll_" in strmsg:
            return
        print >>sys.stdout, strmsg
    mod.logstate = py.log._getstate()
    py.log.setconsumer("llinterp", py.log.STDOUT)
    py.log.setconsumer("llinterp frame", stdout_ignore_ll_functions)
    py.log.setconsumer("llinterp operation", None)


class GCTest(object):

    def setup_class(cls):
        gclltype.prepare_graphs_and_create_gc = gclltype.create_gc
        gclltype.use_gc = cls.GCClass
        from pypy.rpython.memory import gc as gcimpl
        gcimpl.DEBUG_PRINT = False
        
    def teardown_class(cls):
        gclltype.prepare_graphs_and_create_gc =  gclltype.create_no_gc
        gclltype.use_gc = MarkSweepGC
        from pypy.rpython.memory import gc as gcimpl
        gcimpl.DEBUG_PRINT = True

    def test_llinterp_lists(self):
        curr = simulator.current_size
        def malloc_a_lot():
            i = 0
            while i < 10:
                i += 1
                a = [1] * 10
                j = 0
                while j < 20:
                    j += 1
                    a.append(j)
        res = interpret(malloc_a_lot, [])
        assert simulator.current_size - curr < 16000 * INT_SIZE / 4
        print "size before: %s, size after %s" % (curr, simulator.current_size)

    def test_llinterp_tuples(self):
        curr = simulator.current_size
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
        res = interpret(malloc_a_lot, [])
        assert simulator.current_size - curr < 16000 * INT_SIZE / 4
        print "size before: %s, size after %s" % (curr, simulator.current_size)

    def test_global_list(self):
        lst = []
        def append_to_list(i, j):
            lst.append([i] * 50)
            return lst[j][0]
        res = interpret(append_to_list, [0, 0])
        assert res == 0
        for i in range(1, 15):
            res = interpret(append_to_list, [i, i - 1])
            assert res == i - 1 # crashes if constants are not considered roots
            
    def test_string_concatenation(self):
        curr = simulator.current_size
        def concat(j):
            lst = []
            for i in range(j):
                lst.append(str(i))
            return len("".join(lst))
        res = interpret(concat, [100])
        assert res == concat(100)
        assert simulator.current_size - curr < 16000 * INT_SIZE / 4


class GCTestOnLLInterp(GCTest):

    def setup_class(cls):
        gclltype.prepare_graphs_and_create_gc = gclltype.create_gc_run_on_llinterp
        gclltype.use_gc = cls.GCClass
        from pypy.rpython.memory import gc as gcimpl
        gcimpl.DEBUG_PRINT = False

class TestMarkSweepGC(GCTest):
    GCClass = MarkSweepGC

if 0:   ## - - - disabling this: the simulator is getting deprecated
    class TestMarkSweepGCRunningOnLLinterp(GCTestOnLLInterp):
        GCClass = MarkSweepGC

class TestSemiSpaceGC(GCTest):
    GCClass = SemiSpaceGC

class TestSemiSpaceGCRunningOnLLinterp(GCTestOnLLInterp):
    GCClass = SemiSpaceGC

class TestDeferredRefcountingGC(GCTest):
    GCClass = DeferredRefcountingGC

class TestDeferredRefcountingGCRunningOnLLinterp(GCTestOnLLInterp):
    GCClass = DeferredRefcountingGC

