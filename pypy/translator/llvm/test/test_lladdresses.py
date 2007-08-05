import py
from pypy.rpython.memory.lladdress import *
from pypy.annotation.model import SomeAddress, SomeChar
from pypy.rlib.objectmodel import free_non_gc_object

from pypy.translator.llvm.test.runtest import *


def test_null():
    def f():
        return NULL - NULL
    fc = compile_function(f, [])

def test_convert_to_bool():
    def convert_to_bool(x):
        if x:
            return bool(NULL)
        else:
            return bool(NULL + 1)
    fc = compile_function(convert_to_bool, [int])
    res = fc(1)
    assert isinstance(res, int) and not res
    res = fc(0)
    assert isinstance(res, int) and res

def test_memory_access():
    def f(value):
        addr = raw_malloc(16)
        addr.signed[0] = value
        res = addr.signed[0]
        raw_free(addr)
        return res
    fc = compile_function(f, [int])
    res = fc(42)
    assert res == 42
    res = fc(1)
    assert res == 1
    
def test_pointer_arithmetic():
    def f(offset, char):
        char = chr(char)
        addr = raw_malloc(10000)
        same_offset = (addr + 2 * offset - offset) - addr 
        addr.char[offset] = char
        result = (addr + same_offset).char[0]
        raw_free(addr)
        return ord(result)
    fc = compile_function(f, [int, int])
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
    fc = compile_function(f, [int, int])
    res = fc(10, ord("c"))
    assert res == ord("c")

def test_raw_memcopy():
    def f():
        addr = raw_malloc(100)
        addr.signed[0] = 12
        (addr + 10).signed[0] = 42
        (addr + 20).char[0] = "a"
        addr1 = raw_malloc(100)
        raw_memcopy(addr, addr1, 100)
        result = addr1.signed[0] == 12
        result = result and (addr1 + 10).signed[0] == 42
        result = result and (addr1 + 20).char[0] == "a"
        raw_free(addr)
        raw_free(addr1)
        return result
    fc = compile_function(f, [])
    res = fc()
    assert res

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
    fc = compile_function(f, [])
    res = fc()
    assert res == int('011100' * 2, 2)

def test_flavored_malloc_raw():
    class A(object):
        _alloc_flavor_ = "raw"
        def __init__(self, val):
            self.val = val
    def f(x):
        a = A(x + 1)
        result = a.val
        free_non_gc_object(a)
        return result
    fn = compile_function(f, [int])
    assert fn(1) == 2 

# def test_flavored_varmalloc_raw():
#     py.test.skip("test_flavored_varmalloc_raw not working - or maybe it will never to work?")
#     A = lltype.Array(lltype.Signed)
#     VARS = lltype.GcStruct('test', ('a', lltype.Signed), ('b', A))
#     def f(x, y):
#         #s = lltype.flavored_malloc('gc', VARS, x)
#         s = lltype.malloc(VARS, n=x, flavor='gc')
#         s.a = 42
#         s.b[0] = y * 2
#         return s.b[0] - s.a

#     fn = compile_function(f, [int, int])
#     assert fn(2, 24) == 6

def test_flavored_malloc_stack():
    class A(object):
        _alloc_flavor_ = "stack"
        def __init__(self, val):
            self.val = val
    def f(x):
        a = A(x + 1)
        result = a.val
        return result
    fn = compile_function(f, [int])
    assert fn(1) == 2 

def test_fakeaddress():
    S = lltype.GcStruct('s', ('val', lltype.Signed))
    s = lltype.malloc(S)
    s.val = 10
    PtrS = lltype.Ptr(S)
    adr = llmemory.cast_ptr_to_adr(s)
    def f(n):
        s1 = llmemory.cast_adr_to_ptr(adr, PtrS)
        old = s1.val
        s1.val = n
        return old + s1.val
    fn = compile_function(f, [int])
    assert fn(32) == 42

def test_fakeaddress2():
    S1 = lltype.GcStruct("S1", ("x", lltype.Signed), ("y", lltype.Signed))
    PtrS1 = lltype.Ptr(S1)
    S2 = lltype.GcStruct("S2", ("s", S1))

    s2 = lltype.malloc(S2)
    s2.s.x = 123
    s2.s.y = 456

    addr_s2 = llmemory.cast_ptr_to_adr(s2)
    addr_s1 = addr_s2 + llmemory.FieldOffset(S2, 's')

    def f():
        s1 = llmemory.cast_adr_to_ptr(addr_s1, PtrS1)
        return s1.x + s1.y
    
    fn = compile_function(f, [])
    assert f() == 579
    
def test_weakaddress():
    from pypy.rlib.objectmodel import cast_object_to_weakgcaddress
    from pypy.rlib.objectmodel import cast_weakgcaddress_to_object
    from pypy.rpython.lltypesystem.lloperation import llop
    class A(object):
        pass
    def func(i):
        l1 = []
        l2 = []
        for i in range(i):
            a = A()
            l1.append(a)
            l2.append(cast_object_to_weakgcaddress(a))
        return len(l1) == len(l2)
    fn = compile_function(func, [int])
    assert fn(10)
    
