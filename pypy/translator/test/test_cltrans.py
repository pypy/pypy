import autopath
from pypy.tool import test
from pypy.tool.udir import udir
from pypy.translator.test.buildclisp import make_cl_func

class GenCLTestCase(test.IntTestCase):

    #___________________________________
    def my_gcd(a, b):
        r = a % b
        while r:
            a = b
            b = r
            r = a % b
        return b
    def XXXtest_gcd(self):
        # disabled because it's rude to fail just because the clisp
        # common lisp implementation isn't installed.
        # (will arrange to skip the test in that case eventually) -- mwh
        cl_gcd = make_cl_func(self.my_gcd, udir)
        self.assertEquals(cl_gcd(96, 64), 32)

if __name__ == '__main__':
    test.main()
