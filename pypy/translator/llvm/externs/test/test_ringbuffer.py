import py
from pypy.translator.llvm.test.runtest import compile_function as compile
from pypy.translator.llvm.externs import ringbuffer

def test_malloc_something():
    def f(value):
        ringbuffer.initialise()
        buf = ringbuffer.malloc_exception(value)
        buf.signed[0] = 10
        return buf.signed[0]

    fc = compile(f, [int])
    assert fc(16) == f(16)
    assert fc(10) == f(10)
