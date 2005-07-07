import sys
import py

from pypy.translator.llvm2.genllvm import use_boehm_gc
from pypy.translator.llvm2.genllvm import compile_module_function

py.log.setconsumer("test_gc", py.log.STDOUT)
py.log.setconsumer("test_gc database prepare", None)

def test_GC_malloc(): 
    if not use_boehm_gc:
        py.test.skip("test_GC_malloc skipped because Boehm collector library was not found")
        return
    def tuple_getitem(n): 
        x = 666
        i = 0
        while i < n:
            l = (1,2,i,4,5,6,7,8,9,10,11)
            x += l[2]
            i += 1
        return x
    mod,f = compile_module_function(tuple_getitem, [int])
    n = 5000
    result = tuple_getitem(n)
    assert f(n) == result
    get_heap_size = getattr(mod, "GC_get_heap_size_wrapper")
    heap_size_start = get_heap_size()
    for i in range(0,25):
        assert f(n) == result
        heap_size_inc = get_heap_size() - heap_size_start
        assert heap_size_inc < 500000
