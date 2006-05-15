import py
import sys

## from pypy.annotation import model as annmodel
## from pypy.annotation.annrpython import RPythonAnnotator
## from pypy.rpython.rtyper import RPythonTyper
## from pypy.rpython.memory.gc import GCError, MarkSweepGC, SemiSpaceGC
## from pypy.rpython.memory.gc import DeferredRefcountingGC, DummyGC
## from pypy.rpython.memory import support
## from pypy.rpython.memory.lladdress import raw_malloc, raw_free, NULL
## from pypy.rpython.memory.simulator import MemorySimulatorError
## from pypy.rpython.memory import gclltype
## from pypy.rpython.memory.test.test_llinterpsim import interpret
## from pypy.rpython.memory.lladdress import simulator
## from pypy.rpython.objectmodel import free_non_gc_object

## def setup_module(mod):
##     def stdout_ignore_ll_functions(msg):
##         strmsg = str(msg)
##         if "evaluating" in strmsg and "ll_" in strmsg:
##             return
##         print >>sys.stdout, strmsg
##     mod.logstate = py.log._getstate()
##     py.log.setconsumer("llinterp", py.log.STDOUT)
##     py.log.setconsumer("llinterp frame", stdout_ignore_ll_functions)
##     py.log.setconsumer("llinterp operation", None)
##     gclltype.prepare_graphs_and_create_gc = gclltype.create_gc

## def teardown_module(mod):
##     gclltype.prepare_graphs_and_create_gc = gclltype.create_no_gc

## class TestMarkSweepGC(object):
##     def setup_class(cls):
##         cls.prep_old = gclltype.prepare_graphs_and_create_gc
##         cls.old = gclltype.use_gc
##         gclltype.use_gc = MarkSweepGC

##     def teardown_class(cls):
##         gclltype.prepare_graphs_and_create_gc = cls.prep_old.im_func
##         gclltype.use_gc = cls.old

##     def test_llinterp_lists(self):
##         curr = simulator.current_size
##         def malloc_a_lot():
##             i = 0
##             while i < 10:
##                 i += 1
##                 a = [1] * 10
##                 j = 0
##                 while j < 20:
##                     j += 1
##                     a.append(j)
##         res = interpret(malloc_a_lot, [])
##         assert simulator.current_size - curr < 16000 * INT_SIZE / 4
##         print "size before: %s, size after %s" % (curr, simulator.current_size)

##     def test_llinterp_tuples(self):
##         curr = simulator.current_size
##         def malloc_a_lot():
##             i = 0
##             while i < 10:
##                 i += 1
##                 a = (1, 2, i)
##                 b = [a] * 10
##                 j = 0
##                 while j < 20:
##                     j += 1
##                     b.append((1, j, i))
##         res = interpret(malloc_a_lot, [])
##         assert simulator.current_size - curr < 16000 * INT_SIZE / 4
##         print "size before: %s, size after %s" % (curr, simulator.current_size)

##     def test_global_list(self):
##         lst = []
##         def append_to_list(i, j):
##             lst.append([i] * 50)
##             return lst[j][0]
##         res = interpret(append_to_list, [0, 0])
##         assert res == 0
##         for i in range(1, 15):
##             res = interpret(append_to_list, [i, i - 1])
##             assert res == i - 1 # crashes if constants are not considered roots
            
##     def test_string_concatenation(self):
##         curr = simulator.current_size
##         def concat(j):
##             lst = []
##             for i in range(j):
##                 lst.append(str(i))
##             return len("".join(lst))
##         res = interpret(concat, [100])
##         assert res == concat(100)
##         assert simulator.current_size - curr < 16000 * INT_SIZE / 4

## class TestMarkSweepGCRunningOnLLinterp(TestMarkSweepGC):
##     def setup_class(cls):
##         cls.prep_old = gclltype.prepare_graphs_and_create_gc
##         gclltype.prepare_graphs_and_create_gc = gclltype.create_gc_run_on_llinterp
##     def teardown_class(cls):
##         gclltype.prepare_graphs_and_create_gc = cls.prep_old.im_func

## class TestSemiSpaceGC(TestMarkSweepGC):
##     def setup_class(cls):
##         gclltype.use_gc = SemiSpaceGC
##         cls.old = gclltype.use_gc
##     def teardown_class(cls):
##         gclltype.use_gc = cls.old

## class TestSemiSpaceGCRunningOnLLinterp(TestMarkSweepGC):
##     def setup_class(cls):
##         cls.prep_old = gclltype.prepare_graphs_and_create_gc
##         gclltype.prepare_graphs_and_create_gc = gclltype.create_gc_run_on_llinterp
##         gclltype.use_gc = SemiSpaceGC
##         cls.old = gclltype.use_gc

##     def teardown_class(cls):
##         gclltype.prepare_graphs_and_create_gc = cls.prep_old.im_func
##         gclltype.use_gc = cls.old

## class TestDeferredRefcountingGC(TestMarkSweepGC):
##     def setup_class(cls):
##         gclltype.use_gc = DeferredRefcountingGC
##         cls.old = gclltype.use_gc
##     def teardown_class(cls):
##         gclltype.use_gc = cls.old


## class TestDeferredRefcountingGCRunningOnLLinterp(TestMarkSweepGC):
##     def setup_class(cls):
##         cls.prep_old = gclltype.prepare_graphs_and_create_gc
##         gclltype.prepare_graphs_and_create_gc = gclltype.create_gc_run_on_llinterp
##         gclltype.use_gc = DeferredRefcountingGC
##         cls.old = gclltype.use_gc

##     def teardown_class(cls):
##         gclltype.prepare_graphs_and_create_gc = cls.prep_old.im_func
##         gclltype.use_gc = cls.old

## class TestDummyGC(TestMarkSweepGC):
##     def setup_class(cls):
##         gclltype.use_gc = DummyGC
##         cls.old = gclltype.use_gc
##     def teardown_class(cls):
##         gclltype.use_gc = cls.old

## class TestDummyGCRunningOnLLinterp(TestMarkSweepGC):
##     def setup_class(cls):
##         cls.prep_old = gclltype.prepare_graphs_and_create_gc
##         gclltype.prepare_graphs_and_create_gc = gclltype.create_gc_run_on_llinterp
##         gclltype.use_gc = DummyGC
##         cls.old = gclltype.use_gc

##     def teardown_class(cls):
##         gclltype.prepare_graphs_and_create_gc = cls.prep_old.im_func
##         gclltype.use_gc = cls.old

from pypy.translator.c import gc
from pypy.rpython.memory import gctransform
from pypy.rpython.memory.support import INT_SIZE


def rtype(func, inputtypes, specialize=True):
    from pypy.translator.translator import TranslationContext
    t = TranslationContext()
    t.buildannotator().build_types(func, inputtypes)
    if specialize:
        t.buildrtyper().specialize(t)
    return t

class GCTest(object):
    gcpolicy = None

    def runner(self, f, withargs=False, statistics=False):
        if withargs:
            def entrypoint(argv):
                x = int(argv[0])
                y = int(argv[1])
                r = f(x, y)
                return r
        else:
            def entrypoint(argv):
                return f()
            
        from pypy.rpython.llinterp import LLInterpreter
        from pypy.translator.c.genc import CStandaloneBuilder
        from pypy.annotation.listdef import s_list_of_strings

        t = rtype(entrypoint, [s_list_of_strings])
        cbuild = CStandaloneBuilder(t, entrypoint, self.gcpolicy)
        db = cbuild.generate_graphs_for_llinterp()
        entrypointptr = cbuild.getentrypointptr()
        entrygraph = entrypointptr._obj.graph

        r_list_of_strings = t.rtyper.getrepr(s_list_of_strings)

        llinterp = LLInterpreter(t.rtyper)

        # FIIIIISH
        setupgraph = db.gctransformer.frameworkgc_setup_ptr.value._obj.graph
        llinterp.eval_graph(setupgraph, [])
        def run(args):
            ll_argv = r_list_of_strings.convert_const([repr(x) for x in args])
            res = llinterp.eval_graph(entrygraph, [ll_argv])
            return res

        if statistics:
            statisticsgraph = db.gctransformer.statistics_ptr.value._obj.graph
            ll_gc = db.gctransformer.c_const_gc.value
            def statistics():
                return llinterp.eval_graph(statisticsgraph, [ll_gc])
            return run, statistics
        else:
            return run
        
class TestMarkSweepGC(GCTest):

    class gcpolicy(gc.FrameworkGcPolicy):
        class transformerclass(gctransform.FrameworkGCTransformer):
            GC_PARAMS = {'start_heap_size': 4096 }
            
    def test_llinterp_lists(self):
        def malloc_a_lot():
            i = 0
            while i < 10:
                i += 1
                a = [1] * 10
                j = 0
                while j < 30:
                    j += 1
                    a.append(j)
        run, statistics = self.runner(malloc_a_lot, statistics=True)
        run([])
        heap_size = statistics().item0
        assert heap_size < 16000 * INT_SIZE / 4 # xxx

    def test_llinterp_tuples(self):
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
        run, statistics = self.runner(malloc_a_lot, statistics=True)
        run([])
        heap_size = statistics().item0
        assert heap_size < 16000 * INT_SIZE / 4 # xxx                    

    def test_global_list(self):
        class Box:
            def __init__(self):
                self.lst = []
        box = Box()
        def append_to_list(i, j):
            box.lst.append([i] * 50)
            return box.lst[j][0]
        run = self.runner(append_to_list, withargs=True)
        res = run([0, 0])
        assert res == 0
        for i in range(1, 15):
            res = run([i, i - 1])
            assert res == i - 1 # crashes if constants are not considered roots
            
    def test_string_concatenation(self):

        def concat(j, dummy):
            lst = []
            for i in range(j):
                lst.append(str(i))
            return len("".join(lst))
        res = self.runner(concat, withargs=True)([100, 0])
        run, statistics = self.runner(concat, withargs=True, statistics=True)
        res = run([100, 0])
        assert res == concat(100, 0)
        heap_size = statistics().item0
        assert heap_size < 16000 * INT_SIZE / 4 # xxx
