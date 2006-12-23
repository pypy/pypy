import py
from os.path import dirname, join
from pypy.translator.c.test.test_genc import compile
from pypy.jit.codegen.llvm import llvmjit

try:
    from pypy.jit.codegen.llvm import llvmjit
except OSError:
    py.test.skip("can not load libllvmjit library (see ../README.TXT)")

#
def skip_unsupported_platform():
    from sys import platform
    if platform == 'darwin':
        py.test.skip('dynamic vs. static library issue on Darwin. see: http://www.cocoadev.com/index.pl?ApplicationLinkingIssues for more information (FIXME)')

#
llsquare = '''int %square(int %n) {
    %n2 = mul int %n, %n
    ret int %n2
}'''

llmul2 = '''int %mul2(int %n) {
    %n2 = mul int %n, 2
    ret int %n2
}'''

#
lldeadcode = '''int %deadcode(int %n) {
Test:
    %cond = icmp eq int %n, %n
    br bool %cond, label %IfEqual, label %IfUnequal

IfEqual:
    %n2 = mul int %n, 2
    ret int %n2

IfUnequal:
    ret int -1
}'''

#
llfuncA = '''int %func(int %n) {
    %n2 = add int %n, %n
    ret int %n2
}'''

llfuncB = '''int %func(int %n) {
    %n2 = mul int %n, %n
    ret int %n2
}'''

#
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

#
llglobalmul4 = '''%my_global_data = external global int

implementation

int %globalmul4(int %a) {
    %v0 = load int* %my_global_data
    %v1 = mul int %v0, 4
    %v2 = add int %v1, %a
    store int %v2, int* %my_global_data
    ret int %v2
}'''

#
llcall_global_function = '''declare int %my_global_function(int, int, int)

implementation

int %call_global_function(int %n) {
    %v = call int %my_global_function(int 3, int %n, int 7) ;note: maybe tail call?
    ret int %v
}'''

#helpers
def execute(llsource, function_name, param):
    assert llvmjit.parse(llsource)
    function = llvmjit.getNamedFunction(function_name)
    assert function
    return llvmjit.execute(function, param)

#tests...
def test_restart():
    for i in range(3):
        llvmjit.restart()
        assert not llvmjit.getNamedFunction('square')
        assert llvmjit.parse(llsquare)
        assert llvmjit.getNamedFunction('square')

def test_getNamedFunction():
    for i in range(3):
        llvmjit.restart()
        assert not llvmjit.getNamedFunction('square')
        assert not llvmjit.getNamedFunction('square')
        assert llvmjit.parse(llsquare)
        assert llvmjit.getNamedFunction('square')
        assert llvmjit.getNamedFunction('square')

def test_parse():
    llvmjit.restart()
    assert llvmjit.parse(llsquare)

def test_execute():
    llvmjit.restart()
    assert execute(llsquare, 'square', 4) == 4 * 4

def test_execute_nothing():
    llvmjit.restart()
    assert llvmjit.execute(None, 4) == -1 #-1 == no function supplied

def test_execute_multiple():
    llvmjit.restart()
    llvmjit.parse(llsquare)
    llvmjit.parse(llmul2)
    square = llvmjit.getNamedFunction('square')
    mul2   = llvmjit.getNamedFunction('mul2')
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
    llvmjit.parse(llacross1)
    llvmjit.parse(llacross2)
    across1to2 = llvmjit.getNamedFunction('across1to2')
    across2to1 = llvmjit.getNamedFunction('across2to1')
    for i in range(5):
        assert llvmjit.execute(across1to2, i) == my_across1to2(i)
        assert llvmjit.execute(across2to1, i) == my_across2to1(i)

def test_recompile():
    py.test.skip("recompile new function implementation test is work in progress")

    def funcA(n):
        return n + n
    
    def funcB(n):
        return n * n
    llvmjit.restart()
    llvmjit.parse(llfuncA)
    _llfuncA = llvmjit.getNamedFunction('func')
    print '_llfuncA', _llfuncA
    for i in range(5):
        assert llvmjit.execute(_llfuncA, i) == funcA(i)
    llvmjit.freeMachineCodeForFunction(_llfuncA)
    llvmjit.parse(llfuncB)
    _llfuncB = llvmjit.getNamedFunction('func')
    print '_llfuncB', _llfuncB
    llvmjit.recompile(_llfuncB) #note: because %func has changed because of the 2nd parse
    for i in range(5):
        assert llvmjit.execute(_llfuncB, i) == funcB(i)

def test_transform(): #XXX This uses Module transforms, think about Function transforms too.
    llvmjit.restart()
    llvmjit.parse(lldeadcode)
    deadcode = llvmjit.getNamedFunction('deadcode')
    assert llvmjit.execute(deadcode, 10) == 10 * 2
    assert llvmjit.transform(3) #optlevel = [0123]
    assert llvmjit.execute(deadcode, 20) == 20 * 2

def test_modify_global_data():
    llvmjit.restart()
    llvmjit.set_global_data(10)
    assert llvmjit.get_global_data() == 10
    gp_data = llvmjit.get_pointer_to_global_data()
    llvmjit.parse(llglobalmul4)
    p = llvmjit.getNamedGlobal('my_global_data...')
    assert not p
    p = llvmjit.getNamedGlobal('my_global_data')
    assert p
    llvmjit.addGlobalMapping(p, gp_data) #note: should be prior to execute()
    globalmul4 = llvmjit.getNamedFunction('globalmul4')
    assert llvmjit.execute(globalmul4, 5) == 10 * 4 + 5
    assert llvmjit.get_global_data() == 10 * 4 + 5

def test_call_global_function(): #used by PyPy JIT for adding case(s) to a flexswitch
    llvmjit.restart()
    gp_function = llvmjit.get_pointer_to_global_function()
    llvmjit.parse(llcall_global_function)
    p = llvmjit.getNamedFunction('my_global_function...')
    assert not p
    p = llvmjit.getNamedFunction('my_global_function')
    assert p
    llvmjit.addGlobalMapping(p, gp_function) #prior to execute()!
    call_global_function = llvmjit.getNamedFunction('call_global_function')
    assert llvmjit.execute(call_global_function, 5) == 3 + 5 + 7

def DONTtest_functions_with_different_signatures():
    pass

def DONTtest_layers_of_codegenerators():    #e.g. i386 code until function stabilizes then llvm
    pass
    
def test_execute_translation(): #put this one last because it takes the most time
    skip_unsupported_platform()
    llvmjit.restart()
    def f(x):
        return execute(llsquare, 'square', x + 5)
    fn = compile(f, [int])
    res = fn(1)
    assert res == 36
