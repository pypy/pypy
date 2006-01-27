from pypy.rpython.memory.lladdress import *
from pypy.annotation.model import SomeAddress, SomeChar
from pypy.translator.llvm.test.runtest import compile_function as compile
from pypy.rpython.objectmodel import free_non_gc_object                                              
import py

def test_null():
    def f():
        return NULL - NULL
    fc = compile(f, [])

def test_convert_to_bool():
    def convert_to_bool(x):
        if x:
            return bool(NULL)
        else:
            return bool(NULL + 1)
    fc = compile(convert_to_bool, [int])
    res = fc(1)
    assert isinstance(res, int) and not res
    res = fc(0)
    assert isinstance(res, int) and res

def test_memory_access():
    def f(value):
        addr = raw_malloc(16)
        addr.signed[0] = value
        return addr.signed[0]
    fc = compile(f, [int])
    res = fc(42)
    assert res == 42
    res = fc(1)
    assert res == 1

def test_memory_access2():
    def f(value1, value2):
        addr = raw_malloc(16)
        addr.signed[0] = value1
        addr.signed[1] = value2
        return addr.signed[0] + addr.signed[1]
    fc = compile(f, [int, int])
    res = fc(23, 19)
    assert res == 42
    res = fc(42, -59)
    assert res == -17
    
def test_pointer_arithmetic():
    def f(offset, char):
        char = chr(char)
        addr = raw_malloc(10000)
        same_offset = (addr + 2 * offset - offset) - addr 
        addr.char[offset] = char
        result = (addr + same_offset).char[0]
        raw_free(addr)
        return ord(result)
    fc = compile(f, [int, int])
    res = fc(10, ord("c"))
    assert res == ord("c")
    res = fc(12, ord("x"))
    assert res == ord("x")

def test_pointer_arithmetic_inplace():
    def f(offset, char):
        char = chr(char)
        addr = raw_malloc(10000)
        addr += offset
        addr.char[-offset] = char
        addr -= offset
        return ord(addr.char[0])
    fc = compile(f, [int, int])
    res = fc(10, ord("c"))
    assert res == ord("c")

def test_raw_memcopy():
    def f():
        addr = raw_malloc(100)
        addr.signed[0] = 12
        (addr + 16).signed[0] = 42
        (addr + 32).char[0] = "a"
        addr1 = raw_malloc(100)
        raw_memcopy(addr, addr1, 100)
        result = addr1.signed[0] == 12
        result += (addr1 + 16).signed[0] == 42
        result += (addr1 + 32).char[0] == "a"
        return result
    fc = compile(f, [])
    res = fc()
    assert res == 3

def test_pointer_comparison():
    def f():
        result = 0
        for addr1 in [raw_malloc(1), NULL]:
            addr2 = addr1 + 1
            result = result * 2 + int(addr1 == addr2)
            result = result * 2 + int(addr1 != addr2)
            result = result * 2 + int(addr1 <  addr2)
            result = result * 2 + int(addr1 <= addr2)
            result = result * 2 + int(addr1 >  addr2)
            result = result * 2 + int(addr1 >= addr2)
        return result
    fc = compile(f, [])
    res = fc()
    assert res == int('011100' * 2, 2)

def test_flavored_malloc1_raw():
    class A(object):
        _alloc_flavor_ = "raw"
        def __init__(self, val):
            self.val = val
    def f(x):
        a = A(x + 1)
        result = a.val
        free_non_gc_object(a)
        return result
    fn = compile(f, [int])
    assert fn(1) == 2 

def test_flavored_malloc2_raw():
    from pypy.rpython.memory.support import AddressLinkedList

    def f():
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
        a = ll.pop()
        res = a - addr
        ll.free()
        free_non_gc_object(ll)
        raw_free(addr)
        return res
    
    fn = compile(f, [])
    assert fn() == 0 

def test_flavored_varmalloc_raw():
    py.test.skip("flavored_malloc not working?")
    A = lltype.Array(lltype.Signed)
    VARS = lltype.GcStruct('test', ('a', lltype.Signed), ('b', A))
    def f(x, y):
        #s = lltype.flavored_malloc('gc', VARS, x)
        s = lltype.malloc(VARS, n=x, flavor='gc')
        s.a = 42
        s.b[0] = y * 2
        return s.b[0] - s.a

    fn = compile(f, [int, int])
    assert fn(2, 24) == 6

def test_flavored_malloc_alloca():
    class A(object):
        _alloc_flavor_ = "stack"
        def __init__(self, val):
            self.val = val
    def f(x):
        a = A(x + 1)
        result = a.val
        free_non_gc_object(a)
        return result
    fn = compile(f, [int])
    assert fn(1) == 2 
