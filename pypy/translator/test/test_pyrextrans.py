import autopath
from pypy.tool import test
from pypy.tool.udir import udir
from pypy.translator.genpyrex import GenPyrex
from pypy.objspace.flow.model import *
from pypy.translator.tool.buildpyxmodule import build_cfunc

from pypy.translator.test import snippet as t

class TypedPyrexGenTestCase(test.IntTestCase):

    def setUp(self):
        self.space = test.objspace('flow')

    def build_cfunc(self, func):
        try: func = func.im_func
        except AttributeError: pass

        dot = test.Options.verbose >0 and 1 or 0
        options = {
            'simplify' : 1,
            'dot' : dot,
            'inputargtypes' : [int] * func.func_code.co_argcount
            }
        return build_cfunc(func, **options)

    def test_simple_func(self):
        cfunc = self.build_cfunc(t.simple_func)
        self.assertEquals(cfunc(1), 2)

    def test_while_func(self):
        while_func = self.build_cfunc(t.while_func)
        self.assertEquals(while_func(10), 55)

    def test_nested_whiles(self):
        nested_whiles = self.build_cfunc(t.nested_whiles)
        self.assertEquals(nested_whiles(111, 114),
                          '...!...!...!...!...!')

    def test_poor_man_range(self):
        poor_man_range = self.build_cfunc(t.poor_man_range)
        self.assertEquals(poor_man_range(10), range(10))

    def test_simple_id(self):
        #we just want to see, if renaming of parameter works correctly
        #if the first branch is the end branch
        simple_id = self.build_cfunc(t.simple_id)
        self.assertEquals(simple_id(9), 9)

    def test_branch_id(self):
        branch_id = self.build_cfunc(t.branch_id)
        self.assertEquals(branch_id(1, 2, 3), 2)
        self.assertEquals(branch_id(0, 2, 3), 3)

    def test_int_id(self):
        int_id = self.build_cfunc(t.int_id)
        self.assertEquals(int_id(3), 3)

    def dont_test_attrs(self):
        attrs = self.build_cfunc(t.attrs)
        self.assertEquals(attrs(), 9)

    def test_builtinusage(self):
        fun = self.build_cfunc(t.builtinusage)
        self.assertEquals(fun(), 4)

    def test_sieve(self):
        sieve = self.build_cfunc(t.sieve_of_eratosthenes)
        self.assertEquals(sieve(), 1028)

    def test_slice(self):
        half = self.build_cfunc(t.half_of_n)
        self.assertEquals(half(10), 5)

class NoTypePyrexGenTestCase(TypedPyrexGenTestCase):

    def build_cfunc(self, func):
        try: func = func.im_func
        except AttributeError: pass

        dot = test.Options.verbose >0 and 1 or 0
        options = {
            'simplify' : 1,
            'dot' : dot,
            }
        return build_cfunc(func, **options)

if __name__ == '__main__':
    test.main()
