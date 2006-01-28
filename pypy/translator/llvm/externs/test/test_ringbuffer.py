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
