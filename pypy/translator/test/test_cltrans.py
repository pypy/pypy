import autopath
from pypy.tool.udir import udir
import py 
import os

def setup_module(mod): 
    mod.global_cl = os.getenv("PYPY_CL")
    if not mod.global_cl:  
        mod.global_cl = cl_detect()

def cl_detect():
    if is_on_path("clisp"):
        return "clisp"
    if is_on_path("lisp"):
        if is_on_path("cmuclinvoke.sh"):
            return "cmuclinvoke.sh"
    if is_on_path("sbcl"):
        if is_on_path("sbclinvoke.sh"):
            return "sbclinvoke.sh"
    return None

def is_on_path(name):
    try:
        py.path.local.sysfind(name) 
    except py.error.ENOENT: 
        return False 
    else: 
        return True 

def make_cl_func(func, argtypes=[]):
    from pypy.translator.tool.buildcl import _make_cl_func
    return _make_cl_func(func, global_cl, udir, argtypes)


from pypy.translator.test import snippet as t
from pypy.translator.tool.buildcl import Literal

class TestGenCLTestCase:
    objspacename = 'flow'

    def setup_method(self,method):
        if not global_cl:
            py.test.skip("Common Lisp neither configured nor detected.")

    def test_if(self):
        cl_if = make_cl_func(t.if_then_else, [object, object, object])
        assert cl_if(True, 50, 100) == 50
        assert cl_if(False, 50, 100) == 100
        assert cl_if(0, 50, 100) == 100
        assert cl_if(1, 50, 100) == 50
        assert cl_if([], 50, 100) == 100
        assert cl_if([[]], 50, 100) == 50

    def test_gcd(self):
        cl_gcd = make_cl_func(t.my_gcd, [int, int])
        assert cl_gcd(96, 64) == 32

    def test_is_perfect(self): # pun intended
        cl_perfect = make_cl_func(t.is_perfect_number, [int])
        assert cl_perfect(24) == False
        assert cl_perfect(28) == True

    def test_bool(self):
        cl_bool = make_cl_func(t.my_bool, [object])
        assert cl_bool(0) == False
        assert cl_bool(42) == True
        assert cl_bool(True) == True

    def test_contains(self):
        my_contains = make_cl_func(t.my_contains, [list, int])
        assert my_contains([1, 2, 3], 1)
        assert not my_contains([1, 2, 3], 0)
        is_one_or_two = make_cl_func(t.is_one_or_two, [int])
        assert is_one_or_two(2)
        assert not is_one_or_two(3)

    def test_array(self):
        cl_four = make_cl_func(t.two_plus_two)
        assert cl_four() == 4

    def test_sieve(self):
        cl_sieve = make_cl_func(t.sieve_of_eratosthenes)
        assert cl_sieve() == 1028

    def test_easy(self):
        # These are the Pyrex tests which were easy to adopt.
        f1 = make_cl_func(t.simple_func, [int])
        assert f1(1) == 2
        f2 = make_cl_func(t.while_func, [int])
        assert f2(10) == 55
        f3 = make_cl_func(t.simple_id, [int])
        assert f3(9) == 9
        f4 = make_cl_func(t.branch_id, [int, int, int])
        assert f4(1, 2, 3) == 2
        assert f4(0, 2, 3) == 3
        f5 = make_cl_func(t.int_id, [int])
        assert f5(3) == 3
        f6 = make_cl_func(t.time_waster, [int])
        assert f6(30) == 3657

    def test_string(self):
        cl_greet = make_cl_func(t.greet, [str])
        assert cl_greet("world") == "helloworld"
        cl_stringmaker = make_cl_func(t.nested_whiles, [int, int])
        assert cl_stringmaker(111, 114) == (
                          "...!...!...!...!...!")

    def test_for(self):
        cl_python = make_cl_func(t.choose_last)
        assert cl_python() == "python"

    def test_builtin(self):
        cl_builtinusage = make_cl_func(t.builtinusage)
        assert cl_builtinusage() == 4

    def test_slice(self):
        cl_half = make_cl_func(t.half_of_n, [int])
        assert cl_half(10) == 5

    def test_powerset(self):
        cl_powerset = make_cl_func(t.powerset, [int])
        result = cl_powerset(3)
        assert result.__class__ == Literal
        assert result.val == (
                          '#(#() #(0) #(1) #(0 1) #(2) #(0 2) #(1 2) #(0 1 2))')
    def test_yast(self):
        cl_sum = make_cl_func(t.yast, [list]) # yet another sum test
        assert cl_sum(range(12)) == 66


# TODO
# poor_man_range
# - append/reverse. not RPython. delegate?
# attrs
# - attribute. need object. symbol-plist?
# yast
# - need way to specify that argument is list of int.
