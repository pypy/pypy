
import autopath
from pypy.tool import test

from pypy.translator.genpyrex import GenPyrex
from pypy.translator.controlflow import *

from pypy.translator.test.buildpyxmodule import make_module_from_pyxstring
#from pypy.translator.test.make_dot import make_ps

class TestCase(test.IntTestCase):
    def setUp(self):
        self.space = test.objspace('flow')

    def makemod(self, source, fname):
        fun = self.codetest(source, fname)
        fun.source = source
        result = GenPyrex(fun).emitcode()
        return make_module_from_pyxstring(result)

    def codetest(self, source, functionname):
        glob = {}
        exec source in glob
        func = glob[functionname]
        return self.space.build_flow(func)

    def test_simple_func(self):
        src = """
def simple_func(i):
    return i+1
"""
        mod = self.makemod(src, 'simple_func')
        self.assertEquals(mod.simple_func(1), 2)

    def test_while(self):
        src = """
def while_func(i):
    total = 0
    while i > 0:
        total = total + i
        i = i - 1
    return total
"""
        mod = self.makemod(src, 'while_func')
        self.assertEquals(mod.while_func(10), 55)

    def test_nested_whiles(self):
        src = """
def nested_whiles(i, j):
    s = ''
    z = 5
    while z > 0:
        z = z - 1
        u = i
        while u < j:
            u = u + 1
            s = s + '.'
        s = s + '!'
    return s
"""
        mod = self.makemod(src, 'nested_whiles')
        self.assertEquals(mod.nested_whiles(111, 114),
                          '...!...!...!...!...!')

    def dont_yet_test_poor_man_range(self):
        src = """
def poor_man_range(i):
    lst = []
    while i > 0:
        i = i - 1
        lst.append(i)
    lst.reverse()
    return lst
"""
        mod = self.makemod(src, 'poor_man_range')
        self.assertEquals(mod.poor_man_range(10), range(10))

if __name__ == '__main__':
    test.main()
