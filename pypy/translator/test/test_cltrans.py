import autopath
from pypy.tool import test
from pypy.tool.udir import udir
from pypy.translator.test.buildcl import _make_cl_func


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
    elif is_on_path("lisp"):
        if is_on_path("cmuclinvoke.sh"):
            return "cmuclinvoke.sh"
    elif is_on_path("sbcl"):
        if is_on_path("sbclinvoke.sh"):
            return "sbclinvoke.sh"
    return None

def is_on_path(name):
    return os.system("which %s >/dev/null" % name) == 0

global_cl = get_cl()

def make_cl_func(func):
    return _make_cl_func(func, global_cl, udir)


from pypy.translator.test import snippet as t

class GenCLTestCase(test.IntTestCase):

    def setUp(self):
        if not global_cl:
            raise (test.TestSkip,
                   "Common Lisp neither configured nor detected.")

    def test_if_bool(self):
        cl_if = make_cl_func(t.if_then_else)
        self.assertEquals(cl_if(True, 50, 100), 50)
        self.assertEquals(cl_if(False, 50, 100), 100)

    def test_if_int(self):
        cl_if = make_cl_func(t.if_then_else)
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

if __name__ == '__main__':
    test.main()
