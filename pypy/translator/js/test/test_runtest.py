import py
from pypy.translator.js.test.runtest import compile_function

#test returntypes
def test_bool_return():
    def bool_return_False():
        return False
    def bool_return_True():
        return True
    f_false = compile_function(bool_return_False, [])
    assert f_false() == bool_return_False()
    f_true  = compile_function(bool_return_True , [])
    assert f_true()  == bool_return_True()    

def test_int_return():
    def int_return():
        return 42
    f = compile_function(int_return, [])
    assert f() == int_return()

def test_float_return():
    def float_return():
        return 42.5
    f = compile_function(float_return, [])
    assert f() == float_return()

#test paramtypes
def test_bool_param():
    def bool_param(b):
        return b
    f = compile_function(bool_param, [bool])
    assert f(False) == bool_param(False)
    assert f(True ) == bool_param(True )

def test_int_param():
    def int_param(n):
        return n * 2
    f = compile_function(int_param, [int])
    assert f(42) == int_param(42)

def test_float_param():
    def float_param(f):
        return f * 3.0
    f = compile_function(float_param, [float])
    assert f(12.5) == float_param(12.5)

def test_combined_params():
    def combined_params(b, n, f):
        return int(int(b) * 5 + n * 2 + f * 3.0)
    f = compile_function(combined_params, [bool,int,float])
    assert f(False, 13, 12.5) == combined_params(False, 13, 12.5)
    assert f(True , 13, 12.5) == combined_params(True , 13, 12.5)

def test_return_function():
    rp = compile_function.reinterpret
    assert rp('[a,b]') == ["a", "b"]
    #assert rp('(true,[a,b])') == [True, ["a", "b"]]

def test_return_newline():
    def fun_newline():
        return "\n"
    fun = compile_function(fun_newline, [])
    assert fun() == "\n"

##def test_multiple_function():
##    def one():
##        return 1
##    
##    def two(x):
##        return x
##    
##    f = compile_function([one, two], [[], [int]])
##    assert f.call(one) == 1
##    assert f.call(two, 3) == 3
##
