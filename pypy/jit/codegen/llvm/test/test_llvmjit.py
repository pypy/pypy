import py
from os.path import dirname, join
from pypy.translator.c.test.test_genc import compile

try:
    from pypy.jit.codegen.llvm import llvmjit
except OSError:
    py.test.skip("libllvmjit not found (see ../README.TXT)")

#helper data
curdir = dirname(__file__)
square = join(curdir, 'square')
mul2   = join(curdir, 'mul2')

square_src = '''int %square(int %n) {
block0:
    %n2 = mul int %n, %n
    ret int %n2
}'''

mul2_src = '''int %mul2(int %n) {
block0:
    %n2 = mul int %n, 2
    ret int %n2
}'''

#helpers
def execute(filename, funcname, param):
    assert llvmjit.compile(filename)
    return llvmjit.execute(funcname, param)

def execute_src(src, funcname, param):
    assert llvmjit.compile_src(src)
    return llvmjit.execute(funcname, param)

#tests...
def test_restart():
    llvmjit.restart()

def test_execute_translation():
    llvmjit.restart()
    def f(x):
        return execute(square, 'square', x + 5)
    fn = compile(f, [int])
    res = fn(1)
    assert res == 36

def test_compile():
    llvmjit.restart()
    assert llvmjit.compile(square)

def test_execute():
    llvmjit.restart()
    assert execute(square, 'square', 4) == 4 * 4

def test_execute_multiple():
    llvmjit.restart()
    llvmjit.compile(square)
    llvmjit.compile(mul2)
    for i in range(5):
        assert llvmjit.execute('square', i) == i * i
        assert llvmjit.execute('mul2', i) == i * 2

def test_compile_src():
    llvmjit.restart()
    assert llvmjit.compile_src(square_src)

def test_execute_src():
    llvmjit.restart()
    assert execute_src(square_src, 'square', 4) == 4 * 4
    
def test_execute_multiple_src():
    llvmjit.restart()
    llvmjit.compile_src(square_src)
    llvmjit.compile_src(mul2_src)
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

