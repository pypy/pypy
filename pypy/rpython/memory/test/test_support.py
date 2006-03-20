from pypy.rpython.objectmodel import free_non_gc_object
from pypy.rpython.memory.support import AddressLinkedList, FreeList, CHUNK_SIZE
from pypy.rpython.memory import support
from pypy.rpython.memory.lladdress import raw_malloc, raw_free, NULL
from pypy.rpython.memory.test.test_llinterpsim import interpret


class TestAddressLinkedList(object):
    def test_simple_access(self):
        addr = raw_malloc(100)
        ll = AddressLinkedList()
        ll.append(addr)
        ll.append(addr + 1)
        ll.append(addr + 2)
        a = ll.pop()
        assert a - addr == 2
        a = ll.pop()
        assert a - addr == 1
        a = ll.pop()
        assert a == addr
        assert ll.pop() == NULL
        assert ll.pop() == NULL
        ll.append(addr)
        ll.free()
        free_non_gc_object(ll)
        ll = AddressLinkedList()
        ll.append(addr)
        ll.append(addr + 1)
        ll.append(addr + 2)
        ll.free()
        free_non_gc_object(ll)
        raw_free(addr)

    def test_big_access(self):
        addr = raw_malloc(1)
        ll = AddressLinkedList()
        for i in range(3000):
            print i
            ll.append(addr + i)
        for i in range(3000)[::-1]:
            a = ll.pop()
            assert a - addr == i
        for i in range(3000):
            print i
            ll.append(addr + i)
        for i in range(3000)[::-1]:
            a = ll.pop()
            assert a - addr == i
        ll.free()
        free_non_gc_object(ll)
        raw_free(addr)
        
def test_linked_list_annotate():
    def f():
        addr = raw_malloc(100)
        ll = AddressLinkedList()
        ll.append(addr)
        ll.append(addr + 1)
        ll.append(addr + 2)
        a = ll.pop()
        res = (a - addr == 2)
        a = ll.pop()
        res = res and (a - addr == 1)
        a = ll.pop()
        res = res and a == addr
        res = res and (ll.pop() == NULL)
        res = res and (ll.pop() == NULL)
        ll.append(addr)
        for i in range(3000):
            ll.append(addr + i)
        for i in range(2999, -1, -1):
            a = ll.pop()
            res = res and (a - addr == i)
        for i in range(3000):
            ll.append(addr + i)
        for i in range(2999, -1, -1):
            a = ll.pop()
            res = res and (a - addr == i)
        ll.free()
        free_non_gc_object(ll)
        ll = AddressLinkedList()
        ll.append(addr)
        ll.append(addr + 1)
        ll.append(addr + 2)
        ll.free()
        free_non_gc_object(ll)
        raw_free(addr)
        return res
##     a = RPythonAnnotator()
##     res = a.build_types(f, [])
##     a.translator.specialize()
##     a.translator.view()
    assert f()
    # grumpf: make sure that we don't get a polluted class attribute
    AddressLinkedList.unused_chunks = FreeList(CHUNK_SIZE + 2)
    res = interpret(f, [])
    assert res
