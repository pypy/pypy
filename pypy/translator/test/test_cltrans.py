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

    #___________________________________
    def if_then_else(cond, x, y):
        if cond:
            return x
        else:
            return y
    def test_if_bool(self):
        cl_if = make_cl_func(self.if_then_else, self.cl, udir)
        self.assertEquals(cl_if(True, 50, 100), 50)
        self.assertEquals(cl_if(False, 50, 100), 100)
    def test_if_int(self):
        cl_if = make_cl_func(self.if_then_else, self.cl, udir)
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
        cl_gcd = make_cl_func(self.my_gcd, self.cl, udir)
        self.assertEquals(cl_gcd(96, 64), 32)

if __name__ == '__main__':
    test.main()
