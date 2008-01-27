import py
from os.path import dirname, join
from pypy.translator.c.test.test_genc import compile
from pypy.jit.codegen.llvm import llvmjit
from pypy.jit.codegen.llvm.compatibility import define, globalprefix, icmp, i1, i32

py.test.skip("doesn't work right now since it is using rctypes")

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
llsquare = '''%(define)s %(i32)s %(globalprefix)ssquare(%(i32)s %%n) {
    %%n2 = mul %(i32)s %%n, %%n
    ret %(i32)s %%n2
}''' % vars()

llmul2 = '''%(define)s %(i32)s %(globalprefix)smul2(%(i32)s %%n) {
    %%n2 = mul %(i32)s %%n, 2
    ret %(i32)s %%n2
}''' % vars()

#
lldeadcode = '''%(define)s %(i32)s %(globalprefix)sdeadcode(%(i32)s %%n) {
Test:
    %%cond = %(icmp)seq %(i32)s %%n, %%n
    br %(i1)s %%cond, label %%IfEqual, label %%IfUnequal

IfEqual:
    %%n2 = mul %(i32)s %%n, 2
    ret %(i32)s %%n2

IfUnequal:
    ret %(i32)s -1
}''' % vars()

#
llfuncA = '''%(define)s %(i32)s %(globalprefix)sfunc(%(i32)s %%n) {
    %%n2 = add %(i32)s %%n, %%n
    ret %(i32)s %%n2
}''' % vars()

llfuncB = '''%(define)s %(i32)s %(globalprefix)sfunc(%(i32)s %%n) {
    %%n2 = mul %(i32)s %%n, %%n
    ret %(i32)s %%n2
}''' % vars()

#
llacross1 = '''declare %(i32)s %(globalprefix)sacross2(%(i32)s)

implementation

%(define)s %(i32)s %(globalprefix)sacross1(%(i32)s %%n) {
    %%n2 = mul %(i32)s %%n, 3
    ret %(i32)s %%n2
}

%(define)s %(i32)s %(globalprefix)sacross1to2(%(i32)s %%n) {
    %%n2 = add %(i32)s %%n, 5
    %%n3 = call %(i32)s %(globalprefix)sacross2(%(i32)s %%n2)
    ret %(i32)s %%n3
}''' % vars()

llacross2 = '''declare %(i32)s %(globalprefix)sacross1(%(i32)s %%dsf)

implementation

%(define)s %(i32)s %(globalprefix)sacross2(%(i32)s %%n) {
    %%n2 = mul %(i32)s %%n, 7
    ret %(i32)s %%n2
}

%(define)s %(i32)s %(globalprefix)sacross2to1(%(i32)s %%n) {
    %%n2 = add %(i32)s %%n, 9
    %%n3 = call %(i32)s %(globalprefix)sacross1(%(i32)s %%n2)
    ret %(i32)s %%n3
}''' % vars()

#
llglobalmul4 = '''%(globalprefix)smy_global_data = external global %(i32)s

implementation

%(define)s %(i32)s %(globalprefix)sglobalmul4(%(i32)s %%a) {
    %%v0 = load %(i32)s* %(globalprefix)smy_global_data
    %%v1 = mul %(i32)s %%v0, 4
    %%v2 = add %(i32)s %%v1, %%a
    store %(i32)s %%v2, %(i32)s* %(globalprefix)smy_global_data
    ret %(i32)s %%v2
}''' % vars()

#
llcall_global_function = '''declare %(i32)s %(globalprefix)smy_global_function(%(i32)s, %(i32)s, %(i32)s)

implementation

%(define)s %(i32)s %(globalprefix)scall_global_function(%(i32)s %%n) {
    %%v = call %(i32)s %(globalprefix)smy_global_function(%(i32)s 3, %(i32)s %%n, %(i32)s 7) ;note: maybe tail call?
    ret %(i32)s %%v
}''' % vars()

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
