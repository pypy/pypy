from pypy.rlib.objectmodel import free_non_gc_object
from pypy.rpython.memory.support import get_address_linked_list

from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.lltypesystem import lltype, llmemory

class TestAddressLinkedList(object):
    def test_simple_access(self):
        from pypy.rpython.memory.lladdress import raw_malloc, raw_free, NULL
        AddressLinkedList = get_address_linked_list()
        addr = raw_malloc(100)
        ll = AddressLinkedList()
        ll.append(addr)
        ll.append(addr + 1)
        ll.append(addr + 2)
        assert ll.non_empty()
        a = ll.pop()
        assert a - addr == 2
        assert ll.non_empty()
        a = ll.pop()
        assert a - addr == 1
        assert ll.non_empty()
        a = ll.pop()
        assert a == addr
        assert not ll.non_empty()
        ll.append(addr)
        ll.delete()
        ll = AddressLinkedList()
        ll.append(addr)
        ll.append(addr + 1)
        ll.append(addr + 2)
        ll.delete()
        raw_free(addr)

    def test_big_access(self):
        from pypy.rpython.memory.lladdress import raw_malloc, raw_free, NULL        
        AddressLinkedList = get_address_linked_list()
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
        ll.delete()
        raw_free(addr)
        
def test_linked_list_annotate():
    AddressLinkedList = get_address_linked_list(60)
    INT_SIZE = llmemory.sizeof(lltype.Signed)
    def f():
        addr = raw_malloc(INT_SIZE*100)
        ll = AddressLinkedList()
        ll.append(addr)
        ll.append(addr + INT_SIZE*1)
        ll.append(addr + INT_SIZE*2)
        a = ll.pop()
        res = (a - INT_SIZE*2 == addr)
        a = ll.pop()
        res = res and (a - INT_SIZE*1 == addr)
        res = res and ll.non_empty()
        a = ll.pop()
        res = res and a == addr
        res = res and not ll.non_empty()
        ll.append(addr)
        for i in range(300):
            ll.append(addr + INT_SIZE*i)
        for i in range(299, -1, -1):
            a = ll.pop()
            res = res and (a - INT_SIZE*i == addr)
        for i in range(300):
            ll.append(addr + INT_SIZE*i)
        for i in range(299, -1, -1):
            a = ll.pop()
            res = res and (a - INT_SIZE*i == addr)
        ll.delete()
        ll = AddressLinkedList()
        ll.append(addr)
        ll.append(addr + INT_SIZE*1)
        ll.append(addr + INT_SIZE*2)
        ll.delete()
        raw_free(addr)
        return res

    NULL = llmemory.NULL
    raw_malloc, raw_free = llmemory.raw_malloc, llmemory.raw_free
    assert f()
    from pypy.rpython.memory.lladdress import raw_malloc, raw_free
    AddressLinkedList = get_address_linked_list()
    res = interpret(f, [], malloc_check=False)
    assert res
