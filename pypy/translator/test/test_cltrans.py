import autopath
from pypy.tool import test
from pypy.tool.udir import udir
from pypy.translator.test.buildcl import make_cl_func

class GenCLTestCase(test.IntTestCase):

    def setUp(self):
        import os
        cl = os.getenv("PYPY_CL")
        if cl:
            self.cl = cl
        else:
            raise test.TestSkip
    def cl_func(self, func):
        return make_cl_func(func, self.cl, udir)

    #___________________________________
    def if_then_else(cond, x, y):
        if cond:
            return x
        else:
            return y
    def test_if_bool(self):
        cl_if = self.cl_func(self.if_then_else)
        self.assertEquals(cl_if(True, 50, 100), 50)
        self.assertEquals(cl_if(False, 50, 100), 100)
    def test_if_int(self):
        cl_if = self.cl_func(self.if_then_else)
        self.assertEquals(cl_if(0, 50, 100), 100)
        self.assertEquals(cl_if(1, 50, 100), 50)

    #___________________________________
    def my_gcd(a, b):
        r = a % b
        while r:
            a = b
            b = r
            r = a % b
        return b
    def test_gcd(self):
        cl_gcd = self.cl_func(self.my_gcd)
        self.assertEquals(cl_gcd(96, 64), 32)

    #___________________________________
    def is_perfect_number(n):
        div = 1
        sum = 0
        while div < n:
            if n % div == 0:
                sum += div
            div += 1
        return n == sum
    def test_is_perfect(self): # pun intended
        cl_perfect = self.cl_func(self.is_perfect_number)
        self.assertEquals(cl_perfect(24), False)
        self.assertEquals(cl_perfect(28), True)

if __name__ == '__main__':
    test.main()
