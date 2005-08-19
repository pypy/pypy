import py

from pypy.annotation import model as annmodel
from pypy.translator.annrpython import RPythonAnnotator
from pypy.rpython.rtyper import RPythonTyper
from pypy.rpython.memory.gc import GCError, MarkSweepGC
from pypy.rpython.memory.support import AddressLinkedList, INT_SIZE
from pypy.rpython.memory.lladdress import raw_malloc, raw_free, NULL
from pypy.rpython.memory.simulator import MemorySimulatorError
from pypy.rpython.memory import gclltype
from pypy.rpython.memory.test.test_llinterpsim import interpret
from pypy.rpython.memory.lladdress import simulator
from pypy.rpython.objectmodel import free_non_gc_object

def setup_module(mod):
    mod.logstate = py.log._getstate()
    py.log.setconsumer("llinterp", py.log.STDOUT)
    py.log.setconsumer("llinterp operation", None)
    gclltype.prepare_graphs_and_create_gc = gclltype.create_mark_sweep_gc

def teardown_module(mod):
    gclltype.prepare_graphs_and_create_gc = gclltype.create_no_gc

class PseudoObjectModel(object):
    """Object model for testing purposes: you can specify roots and a
    layout_mapping which is a dictionary of typeids to a list of offsets of
    pointers in an object"""
    def __init__(self, roots, layout_mapping, size_mapping):
        self.roots = roots
        self.layout_mapping = layout_mapping
        self.size_mapping = size_mapping

    def get_roots(self):
        self.roots
        ll = AddressLinkedList()
        for root in self.roots:
            ll.append(root)
        return ll

    def is_varsize(self, typeid):
        False

    def fixed_size(self, typeid):
        return self.size_mapping[typeid]

    def offsets_to_gc_pointers(self, typeid):
        return self.layout_mapping[typeid]

class TestMarkSweepGC(object):
    def test_simple(self):
        variables = raw_malloc(4 * INT_SIZE)
        roots = [variables + i * INT_SIZE for i in range(4)]
        layout0 = [] #int
        layout1 = [0, INT_SIZE] #(ptr, ptr)
        om = PseudoObjectModel(roots, {0: layout0, 1: layout1}, {0: INT_SIZE, 1: 2 * INT_SIZE})
        gc = MarkSweepGC(om, 2 ** 16)
        variables.address[0] = gc.malloc(0)
        variables.address[1] = gc.malloc(0)
        variables.address[2] = gc.malloc(0)
        variables.address[3] = gc.malloc(0)
        print "roots", roots
        gc.collect() #does not crash
        addr = gc.malloc(0)
        addr.signed[0] = 1
        print "roots", roots
        gc.collect()
        py.test.raises(MemorySimulatorError, "addr.signed[0]")
        variables.address[0] = gc.malloc(1)
        variables.address[0].address[0] = variables.address[1]
        variables.address[0].address[1] = NULL
        print "roots", roots
        gc.collect() #does not crash
        addr0 = gc.malloc(1)
        addr0.address[1] = NULL
        addr1 = gc.malloc(1)
        addr1.address[0] = addr1.address[1] = NULL
        addr0.address[0] = addr1
        addr2 = variables.address[1]
        print "addr0, addr1, addr2 =", addr0, addr1, addr2
        variables.address[1] == NULL
        variables.address[0].address[0] = NULL
        print "roots", roots
        gc.collect()
        py.test.raises(MemorySimulatorError, "addr0.signed[0]")
        py.test.raises(MemorySimulatorError, "addr1.signed[0]")
        py.test.raises(MemorySimulatorError, "addr2.signed[0]")

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
        assert simulator.current_size - curr < 16000
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
        assert simulator.current_size - curr < 16000
        print "size before: %s, size after %s" % (curr, simulator.current_size)

    def test_global_list(self):
        lst = []
        def append_to_list(i, j):
            lst.append([i] * 500)
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
        assert simulator.current_size - curr < 16000
