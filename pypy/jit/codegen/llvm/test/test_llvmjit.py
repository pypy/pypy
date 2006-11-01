import py

try:
    from pypy.jit.codegen.llvm import llvmjit
except OSError:
    py.test.skip("llvmjit library not found (see ../README.TXT)")

def test_testme():
    assert llvmjit.testme(10) == 20
