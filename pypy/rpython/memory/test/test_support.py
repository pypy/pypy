from pypy.rpython.memory.gc import free_non_gc_object
from pypy.rpython.memory.support import AddressLinkedList
from pypy.rpython.memory.lladdress import raw_malloc, raw_free, NULL

class TestAddressLinkedList(object):
    def test_simple_access(self):
        addr = raw_malloc(100)
        ll = AddressLinkedList()
        ll.append(addr)
        ll.append(addr + 1)
        ll.append(addr + 2)
        a = ll.pop()
        assert a == addr
        a = ll.pop()
        assert a - addr == 1
        a = ll.pop()
        assert a - addr == 2
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
        
