import py

from pypy.rpython.memory.gc import free_non_gc_object, GCError, MarkSweepGC
from pypy.rpython.memory.support import AddressLinkedList, INT_SIZE
from pypy.rpython.memory.lladdress import raw_malloc, raw_free, NULL
from pypy.rpython.memory.simulator import MemorySimulatorError
from pypy.rpython.memory import gclltype
from pypy.rpython.memory.test.test_llinterpsim import interpret

def setup_module(mod):
    mod.logstate = py.log._getstate()
    py.log.setconsumer("llinterp", py.log.STDOUT)
    py.log.setconsumer("llinterp operation", None)

def test_free_non_gc_object():
    class TestClass(object):
        _raw_allocate_ = True
        def __init__(self, a):
            self.a = a
        def method1(self):
            return self.a
        def method2(self):
            return 42
    class TestClass2(object):
        pass
    t = TestClass(1)
    assert t.method1() == 1
    assert t.method2() == 42
    free_non_gc_object(t)
    py.test.raises(GCError, "t.method1()")
    py.test.raises(GCError, "t.method2()") 
    py.test.raises(GCError, "t.a")
    py.test.raises(AssertionError, "free_non_gc_object(TestClass2())")


class PseudoObjectModel(object):
    """Object model for testing purposes: you can specify roots and a
    layout_mapping which is a dictionary of typeids to a list of offsets of
    pointers in an object"""
    def __init__(self, roots, layout_mapping):
        self.roots = roots
        self.layout_mapping = layout_mapping

    def get_roots(self):
        self.roots
        ll = AddressLinkedList()
        for root in self.roots:
            ll.append(root)
        return ll

    def get_contained_pointers(self, addr, typeid):
        if addr is NULL:
            return AddressLinkedList()
        layout = self.layout_mapping[typeid]
        result = AddressLinkedList()
        for offset in layout:
            result.append(addr + offset)
        return result

class TestMarkSweepGC(object):
    def test_simple(self):
        variables = raw_malloc(4 * INT_SIZE)
        roots = [variables + i * INT_SIZE for i in range(4)]
        layout0 = [] #int
        layout1 = [0, INT_SIZE] #(ptr, ptr)
        om = PseudoObjectModel(roots, {0: layout0, 1: layout1})
        gc = MarkSweepGC(om, 2 ** 16)
        variables.address[0] = gc.malloc(0, INT_SIZE)
        variables.address[1] = gc.malloc(0, INT_SIZE)
        variables.address[2] = gc.malloc(0, INT_SIZE)
        variables.address[3] = gc.malloc(0, INT_SIZE)
        print "roots", roots
        gc.collect() #does not crash
        addr = gc.malloc(0, INT_SIZE)
        addr.signed[0] = 1
        print "roots", roots
        gc.collect()
        py.test.raises(MemorySimulatorError, "addr.signed[0]")
        variables.address[0] = gc.malloc(1, 2 * INT_SIZE)
        variables.address[0].address[0] = variables.address[1]
        variables.address[0].address[1] = NULL
        print "roots", roots
        gc.collect() #does not crash
        addr0 = gc.malloc(1, 2 * INT_SIZE)
        addr0.address[1] = NULL
        addr1 = gc.malloc(1, 2 * INT_SIZE)
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
        from pypy.rpython.memory.lladdress import simulator
        gclltype.create_gc = gclltype.create_mark_sweep_gc
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
        from pypy.rpython.memory.lladdress import simulator
        gclltype.create_gc = gclltype.create_mark_sweep_gc
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
