import autopath
from pypy.tool import testit
from pypy.tool.udir import udir
from pypy.translator.genpyrex import GenPyrex
from pypy.objspace.flow.model import *
from pypy.translator.tool.buildpyxmodule import build_cfunc
from pypy.translator.translator import Translator

from pypy.translator.test import snippet 

class NoTypePyrexGenTestCase(testit.IntTestCase):

    def setUp(self):
        self.space = testit.objspace('flow')

    def build_cfunc(self, func):
        try: func = func.im_func
        except AttributeError: pass

        dot = testit.Options.verbose >0 and 1 or 0
        options = {
            'simplify' : 1,
            'dot' : dot,
            }
        return build_cfunc(func, **options)

    def test_simple_func(self):
        cfunc = self.build_cfunc(snippet.simple_func)
        self.assertEquals(cfunc(1), 2)

    def test_while_func(self):
        while_func = self.build_cfunc(snippet.while_func)
        self.assertEquals(while_func(10), 55)

    def test_nested_whiles(self):
        nested_whiles = self.build_cfunc(snippet.nested_whiles)
        self.assertEquals(nested_whiles(111, 114),
                          '...!...!...!...!...!')

    def test_poor_man_range(self):
        poor_man_range = self.build_cfunc(snippet.poor_man_range)
        self.assertEquals(poor_man_range(10), range(10))

    def poor_man_rev_range(self):
        poor_man_rev_range = self.build_cfunc(snippet.poor_man_rev_range)
        self.assertEquals(poor_man_rev_range(10), range(9,-1,-1))

    def test_simple_id(self):
        #we just want to see, if renaming of parameter works correctly
        #if the first branch is the end branch
        simple_id = self.build_cfunc(snippet.simple_id)
        self.assertEquals(simple_id(9), 9)

    def test_branch_id(self):
        branch_id = self.build_cfunc(snippet.branch_id)
        self.assertEquals(branch_id(1, 2, 3), 2)
        self.assertEquals(branch_id(0, 2, 3), 3)

    def test_int_id(self):
        int_id = self.build_cfunc(snippet.int_id)
        self.assertEquals(int_id(3), 3)

    def dont_test_attrs(self):
        attrs = self.build_cfunc(snippet.attrs)
        self.assertEquals(attrs(), 9)

    def test_builtinusage(self):
        fun = self.build_cfunc(snippet.builtinusage)
        self.assertEquals(fun(), 4)

    def test_sieve(self):
        sieve = self.build_cfunc(snippet.sieve_of_eratosthenes)
        self.assertEquals(sieve(), 1028)

    def test_slice(self):
        half = self.build_cfunc(snippet.half_of_n)
        self.assertEquals(half(10), 5)

    def test_poly_branch(self):
        poly_branch = self.build_cfunc(snippet.poly_branch)
        self.assertEquals(poly_branch(10), [1,2,3]*2)
        self.assertEquals(poly_branch(0), ['a','b','c']*2)

    def test_and(self):
        sand = self.build_cfunc(snippet.s_and)
        self.assertEquals(sand(5, 6), "yes")
        self.assertEquals(sand(5, 0), "no")
        self.assertEquals(sand(0, 6), "no")
        self.assertEquals(sand(0, 0), "no")

class TypedTestCase(testit.IntTestCase):

    def getcompiled(self, func):
        t = Translator(func) 
        t.simplify()
        # builds starting-types from func_defs 
        argstypelist = []
        if func.func_defaults:
            for spec in func.func_defaults:
                if isinstance(spec, tuple):
                    spec = spec[0] # use the first type only for the tests
                argstypelist.append(spec)
        t.annotate(argstypelist) 
        return t.compile()

    def test_set_attr(self):
        set_attr = self.getcompiled(snippet.set_attr)
        self.assertEquals(set_attr(), 2)

    def test_inheritance2(self):
        inheritance2 = self.getcompiled(snippet.inheritance2)
        self.assertEquals(inheritance2(), ((-12, -12), (3, "world")))

    def test_factorial2(self):
        factorial2 = self.getcompiled(snippet.factorial2)
        self.assertEquals(factorial2(5), 120)

    def test_factorial(self):
        factorial = self.getcompiled(snippet.factorial)
        self.assertEquals(factorial(5), 120)

    def test_simple_method(self):
        simple_method = self.getcompiled(snippet.simple_method)
        self.assertEquals(simple_method(55), 55)

    def test_sieve_of_eratosthenes(self):
        sieve_of_eratosthenes = self.getcompiled(snippet.sieve_of_eratosthenes)
        self.assertEquals(sieve_of_eratosthenes(), 1028)

    def test_nested_whiles(self):
        nested_whiles = self.getcompiled(snippet.nested_whiles)
        self.assertEquals(nested_whiles(5,3), '!!!!!')

    def xxxtest_call_five(self):
        call_five = self.getcompiled(snippet.call_five)
        self.assertEquals(call_five(), [5])

if __name__ == '__main__':
    testit.main()
