import autopath
from pypy.tool import test
from pypy.tool.udir import udir
from pypy.translator.genpyrex import GenPyrex
from pypy.translator.flowmodel import *
from pypy.translator.test.buildpyxmodule import make_module_from_pyxstring

make_dot = 0

if make_dot: 
    from pypy.translator.test.make_dot import make_dot
else:
    def make_dot(*args): pass

class PyrexGenTestCase(test.IntTestCase):
    def setUp(self):
        self.space = test.objspace('flow')

    def make_cfunc(self, func):
        """ make a pyrex-generated cfunction from the given func """
        import inspect
        try:
            func = func.im_func
        except AttributeError:
            pass
        name = func.func_name
        funcgraph = self.space.build_flow(func)
        from pypy.translator.simplify import eliminate_empty_blocks
        #eliminate_empty_blocks(funcgraph)
        funcgraph.source = inspect.getsource(func)
        result = GenPyrex(funcgraph).emitcode()
        make_dot(funcgraph, udir, 'ps')
        mod = make_module_from_pyxstring(name, udir, result)
        return getattr(mod, name)

    #____________________________________________________
    def simple_func(i):
        return i+1

    def test_simple_func(self):
        cfunc = self.make_cfunc(self.simple_func)
        self.assertEquals(cfunc(1), 2)

    #____________________________________________________
    def while_func(i):
        total = 0
        while i > 0:
            total = total + i
            i = i - 1
        return total

    def test_while_func(self):
        while_func = self.make_cfunc(self.while_func)
        self.assertEquals(while_func(10), 55)

    #____________________________________________________
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

    def test_nested_whiles(self):
        nested_whiles = self.make_cfunc(self.nested_whiles)
        self.assertEquals(nested_whiles(111, 114),
                          '...!...!...!...!...!')

    #____________________________________________________
    def poor_man_range(i):
        lst = []
        while i > 0:
            i = i - 1
            lst.append(i)
        lst.reverse()
        return lst

    def test_poor_man_range(self):
        poor_man_range = self.make_cfunc(self.poor_man_range)
        self.assertEquals(poor_man_range(10), range(10))

    #____________________________________________________

    def attrs():
        def b(): pass
        b.f = 4
        b.g = 5

        return b.f + b.g

    def _test_attrs(self):
        attrs = self.make_cfunc(self.attrs)
        self.assertEquals(attrs(), 9)

    #_____________________________________________________

    def builtinusage():
        return pow(2,2)

    def test_builtinusage(self):
        fun = self.make_cfunc(self.builtinusage)
        self.assertEquals(fun(), 4)


if __name__ == '__main__':
    test.main()
