import py
from os.path import dirname, join
from pypy.translator.c.test.test_genc import compile

try:
    from pypy.jit.codegen.llvm import llvmjit
except OSError:
    py.test.skip("libllvmjit not found (see ../README.TXT)")

curdir = dirname(__file__)
square = join(curdir, 'square')

def test_testme():
    assert llvmjit.testme(10) == 20

def test_testme_compile():
    def f(x):
        return llvmjit.testme(20+x)
    fn = compile(f, [int])
    res = fn(1)
    assert res == 42

def test_compile():
    assert llvmjit.compile(square)

def test_compiled():
    compiled = llvmjit.compile(square)
    assert llvmjit.execute(compiled, 'square', 4) == 4 * 4

