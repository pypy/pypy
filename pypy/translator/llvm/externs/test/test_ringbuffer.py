import py
from pypy.tool.udir import udir

from pypy.translator.llvm.test.runtest import compile_function as compile
from pypy.translator.llvm.externs import ringbuffer
from pypy.translator.llvm import genllvm

def teardown_module(self):
    for n in ["ccode.c", "ccode.ll"]:
        f = udir.join(n)
        if f.check(exists=1):
            f.remove()
    genllvm.GenLLVM.llexterns_header = None
    genllvm.GenLLVM.llexterns_functions = None
    
def test_malloc_something():
    def f(value):
        ringbuffer.ringbuffer_initialise()
        buf = ringbuffer.ringbuffer_malloc(value)
        buf.signed[0] = 10
        return buf.signed[0]

    fc = compile(f, [int])
    assert fc(16) == f(16)
    assert fc(10) == f(10)
    
def test_ring():
    def f(init, n_bytes, value):
        if init:
            ringbuffer.ringbuffer_initialise()
            return 42
        buf           = ringbuffer.ringbuffer_malloc(n_bytes)
        old_value     = buf.signed[0]
        buf.signed[0] = value
        return old_value

    fc = compile(f, [int, int, int])
    res1 = fc(True, 0, 0)
    res2 = f(True, 0, 0)
    assert res1 == 42
    assert res1 == res2
    for i in range(ringbuffer.size*3):
        res1 = fc(False, ringbuffer.entry_maxsize, i)
        res2 = f(False, ringbuffer.entry_maxsize, i)
        assert res1 == res2
        n = ringbuffer.size / ringbuffer.entry_maxsize
        if i >= n:
            assert res1 == i - n
            #print res1, i, n
