import py
from os.path import dirname, join
from pypy.translator.c.test.test_genc import compile

try:
    from pypy.jit.codegen.llvm import llvmjit
except OSError:
    py.test.skip("libllvmjit not found (see ../README.TXT)")

curdir = dirname(__file__)
square = join(curdir, 'square')
mul2   = join(curdir, 'mul2')

def execute(filename, funcname, param):
    assert llvmjit.compile(filename)
    return llvmjit.execute(funcname, param)

def test_execute_compile():
    def f(x):
        return execute(square, 'square', x + 5)
    fn = compile(f, [int])
    res = fn(1)
    assert res == 36

def test_compile():
    assert llvmjit.compile(square)

def test_compiled():
    assert execute(square, 'square', 4) == 4 * 4

def test_compiled2():
    llvmjit.compile(square)
    llvmjit.compile(mul2)
    for i in range(5):
        assert llvmjit.execute('square', i) == i * i
        assert llvmjit.execute('mul2', i) == i * 2

def DONTtest_execute_accross_module():
    pass

def DONTtest_modify_global_data():
    pass

def DONTtest_call_back_to_parent(): #call JIT-compiler again for it to add case(s) to flexswitch
    pass

def DONTtest_delete_function():
    pass

def DONTtest_functions_with_different_signatures():
    pass

def DONTtest_llvm_transformations():
    pass

def DONTtest_layers_of_codegenerators():    #e.g. i386 code until function stabilizes then llvm
    pass

def DONTtest_inmemory_ll_and_bc_files():
    pass

