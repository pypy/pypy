import py
from sys import platform
from os.path import dirname, join
from pypy.translator.c.test.test_genc import compile

from pypy.jit.codegen.llvm import llvmjit

try:
    from pypy.jit.codegen.llvm import llvmjit
except OSError:
    py.test.skip("can not load libllvmjit library (see ../README.TXT)")

#helper data
curdir = dirname(__file__)

llsquare = '''int %square(int %n) {
    %n2 = mul int %n, %n
    ret int %n2
}'''

llmul2 = '''int %mul2(int %n) {
    %n2 = mul int %n, 2
    ret int %n2
}'''

lldeadcode = '''int %deadcode(int %n) {
Test:
    %cond = seteq int %n, %n
    br bool %cond, label %IfEqual, label %IfUnequal

IfEqual:
    %n2 = mul int %n, 2
    ret int %n2

IfUnequal:
    ret int -1
}'''

llacross1 = '''declare int %across2(int)

implementation

int %across1(int %n) {
    %n2 = mul int %n, 3
    ret int %n2
}

int %across1to2(int %n) {
    %n2 = add int %n, 5
    %n3 = call int %across2(int %n2)
    ret int %n3
}'''

llacross2 = '''declare int %across1(int %dsf)

implementation

int %across2(int %n) {
    %n2 = mul int %n, 7
    ret int %n2
}

int %across2to1(int %n) {
    %n2 = add int %n, 9
    %n3 = call int %across1(int %n2)
    ret int %n3
}'''

llglobalmul4 = '''%my_global_data = external global int

implementation

int %globalmul4(int %a) {
    %v0 = load int* %my_global_data
    %v1 = mul int %v0, 4
    %v2 = add int %v1, %a
    store int %v2, int* %my_global_data
    ret int %v2
}'''

#helpers
def execute(llsource, function_name, param):
    assert llvmjit.compile(llsource)
    function = llvmjit.find_function(function_name)
    assert function
    return llvmjit.execute(function, param)

#tests...
def test_restart():
    for i in range(3):
        llvmjit.restart()
        assert not llvmjit.find_function('square')
        assert llvmjit.compile(llsquare)
        assert llvmjit.find_function('square')

def test_find_function():
    for i in range(3):
        llvmjit.restart()
        assert not llvmjit.find_function('square')
        assert not llvmjit.find_function('square')
        assert llvmjit.compile(llsquare)
        assert llvmjit.find_function('square')
        assert llvmjit.find_function('square')

def test_compile():
    llvmjit.restart()
    assert llvmjit.compile(llsquare)

def test_execute():
    llvmjit.restart()
    assert execute(llsquare, 'square', 4) == 4 * 4

def test_execute_nothing():
    llvmjit.restart()
    assert llvmjit.execute(None, 4) == -1 #-1 == no function supplied

def test_execute_multiple():
    llvmjit.restart()
    llvmjit.compile(llsquare)
    llvmjit.compile(llmul2)
    square = llvmjit.find_function('square')
    mul2   = llvmjit.find_function('mul2')
    for i in range(5):
        assert llvmjit.execute(square, i) == i * i
        assert llvmjit.execute(mul2  , i) == i * 2

def test_execute_across_module():
    def my_across1(n):
        return n * 3

    def my_across1to2(n):
        return my_across2(n + 5)

    def my_across2(n):
        return n * 7

    def my_across2to1(n):
        return my_across1(n + 9)

    llvmjit.restart()
    llvmjit.compile(llacross1)
    llvmjit.compile(llacross2)
    across1to2 = llvmjit.find_function('across1to2')
    across2to1 = llvmjit.find_function('across2to1')
    for i in range(5):
        assert llvmjit.execute(across1to2, i) == my_across1to2(i)
        assert llvmjit.execute(across2to1, i) == my_across2to1(i)

def test_transform(): #XXX This uses Module transforms, think about Function transforms too.
    llvmjit.restart()
    llvmjit.compile(lldeadcode)
    deadcode = llvmjit.find_function('deadcode')
    assert llvmjit.execute(deadcode, 10) == 10 * 2

    #XXX enable this part of the test asap
    #assert not llvmjit.transform("instcombine printm verify")
    assert llvmjit.execute(deadcode, 20) == 20 * 2

    assert llvmjit.transform("instcombine simplifycfg printm verify")
    assert llvmjit.execute(deadcode, 30) == 30 * 2

def test_modify_global_data():
    llvmjit.restart()
    llvmjit.set_global_data(10)
    assert llvmjit.get_global_data() == 10
    gp_data = llvmjit.get_pointer_to_global_data()
    llvmjit.compile(llglobalmul4)
    llvmjit.add_global_mapping('my_global_data', gp_data) #note: should be prior to execute()
    globalmul4 = llvmjit.find_function('globalmul4')
    assert llvmjit.execute(globalmul4, 5) == 10 * 4 + 5
    assert llvmjit.get_global_data() == 10 * 4 + 5

def DONTtest_call_back_to_parent(): #call JIT-compiler again for it to add case(s) to flexswitch
    pass

def DONTtest_delete_function():
    pass

def DONTtest_functions_with_different_signatures():
    pass

def DONTtest_layers_of_codegenerators():    #e.g. i386 code until function stabilizes then llvm
    pass
    
def test_execute_translation(): #put this one last because it takes the most time
    if platform == 'darwin':
        py.test.skip('dynamic vs. static library issue. see: http://www.cocoadev.com/index.pl?ApplicationLinkingIssues for more information (needs to be fixed)')

    llvmjit.restart()
    def f(x):
        return execute(llsquare, 'square', x + 5)
    fn = compile(f, [int])
    res = fn(1)
    assert res == 36
