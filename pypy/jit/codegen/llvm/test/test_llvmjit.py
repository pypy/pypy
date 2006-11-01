import py
from pypy.translator.c.test.test_genc import compile

try:
    from pypy.jit.codegen.llvm import llvmjit
except OSError:
    py.test.skip("llvmjit library not found (see ../README.TXT)")

def test_testme():
    assert llvmjit.testme(10) == 20

def test_testme_compile():
    def f(x):
        return llvmjit.testme(20+x)
    fn = compile(f, [int])
    res = fn(1)
    assert res == 42
