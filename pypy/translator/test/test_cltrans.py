import autopath
from pypy.tool import test
from pypy.tool.udir import udir


import os

def get_cl():
    cl = os.getenv("PYPY_CL")
    if cl: return cl
    cl = cl_detect()
    if cl: return cl
    return None

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
    return os.system("which %s >/dev/null" % name) == 0

global_cl = get_cl()

def make_cl_func(func, argtypes=[]):
    from pypy.translator.tool.buildcl import _make_cl_func
    return _make_cl_func(func, global_cl, udir, argtypes)


from pypy.translator.test import snippet as t
from pypy.translator.tool.buildcl import Literal

class GenCLTestCase(test.IntTestCase):

    def setUp(self):
        if not global_cl:
            raise (test.TestSkip,
                   "Common Lisp neither configured nor detected.")

    def test_if(self):
        cl_if = make_cl_func(t.if_then_else)
        self.assertEquals(cl_if(True, 50, 100), 50)
        self.assertEquals(cl_if(False, 50, 100), 100)
        self.assertEquals(cl_if(0, 50, 100), 100)
        self.assertEquals(cl_if(1, 50, 100), 50)

    def test_gcd(self):
        cl_gcd = make_cl_func(t.my_gcd)
        self.assertEquals(cl_gcd(96, 64), 32)

    def test_is_perfect(self): # pun intended
        cl_perfect = make_cl_func(t.is_perfect_number)
        self.assertEquals(cl_perfect(24), False)
        self.assertEquals(cl_perfect(28), True)

    def test_bool(self):
        cl_bool = make_cl_func(t.my_bool)
        self.assertEquals(cl_bool(0), False)
        self.assertEquals(cl_bool(42), True)
        self.assertEquals(cl_bool(True), True)

    def test_array(self):
        cl_four = make_cl_func(t.two_plus_two)
        self.assertEquals(cl_four(), 4)

    def test_sieve(self):
        cl_sieve = make_cl_func(t.sieve_of_eratosthenes)
        self.assertEquals(cl_sieve(), 1028)

    def test_easy(self):
        # These are the Pyrex tests which were easy to adopt.
        f1 = make_cl_func(t.simple_func)
        self.assertEquals(f1(1), 2)
        f2 = make_cl_func(t.while_func)
        self.assertEquals(f2(10), 55)
        f3 = make_cl_func(t.simple_id)
        self.assertEquals(f3(9), 9)
        f4 = make_cl_func(t.branch_id)
        self.assertEquals(f4(1, 2, 3), 2)
        self.assertEquals(f4(0, 2, 3), 3)
        f5 = make_cl_func(t.int_id)
        self.assertEquals(f5(3), 3)
        f6 = make_cl_func(t.time_waster)
        self.assertEquals(f6(30), 3657)

    def test_string(self):
        cl_greet = make_cl_func(t.greet, [str])
        self.assertEquals(cl_greet("world"), "helloworld")
        cl_stringmaker = make_cl_func(t.nested_whiles)
        self.assertEquals(cl_stringmaker(111, 114),
                          "...!...!...!...!...!")

    def test_for(self):
        cl_python = make_cl_func(t.choose_last)
        self.assertEquals(cl_python(), "python")

    def test_builtin(self):
        cl_builtinusage = make_cl_func(t.builtinusage)
        self.assertEquals(cl_builtinusage(), 4)

    def test_slice(self):
        cl_half = make_cl_func(t.half_of_n)
        self.assertEquals(cl_half(10), 5)

    def test_powerset(self):
        cl_powerset = make_cl_func(t.powerset, [int])
        result = cl_powerset(3)
        self.assertEquals(result.__class__, Literal)
        self.assertEquals(result.val,
                          '#(#() #(0) #(1) #(0 1) #(2) #(0 2) #(1 2) #(0 1 2))')

if __name__ == '__main__':
    test.main()
