import autopath
from pypy.tool import test
from pypy.tool.udir import udir
from pypy.translator.genpyrex import GenPyrex
from pypy.translator.flowmodel import *
from pypy.translator.test.buildpyxmodule import make_module_from_pyxstring


make_dot = False

if make_dot: 
    from pypy.translator.test.make_dot import make_dot
else:
    def make_dot(*args): pass


from pypy.translator.test import snippet as t

class TypedPyrexTestCase(test.IntTestCase):

    def setUp(self):
        self.space = test.objspace('flow')

    def make_cfunc(self, func, input_arg_types):
        """ make a pyrex-generated cfunction from the given func """
        import inspect
        try:
            func = func.im_func
        except AttributeError:
            pass
        name = func.func_name
        funcgraph = self.space.build_flow(func)
        funcgraph.source = inspect.getsource(func)
        genpyrex = GenPyrex(funcgraph)
        genpyrex.annotate(input_arg_types)
        result = genpyrex.emitcode()
        make_dot(funcgraph, udir, 'ps')
        mod = make_module_from_pyxstring(name, udir, result)
        return getattr(mod, name)

    def test_simple_func(self):
        cfunc = self.make_cfunc(t.simple_func, [int])
        self.assertEquals(cfunc(1), 2)

    def test_while_func(self):
        while_func = self.make_cfunc(t.while_func, [int])
        self.assertEquals(while_func(10), 55)

    def test_yast(self):
        yast = self.make_cfunc(t.yast, [list])
        self.assertEquals(yast(range(12)), 66)

    def test_nested_whiles(self):
        nested_whiles = self.make_cfunc(t.nested_whiles, [int, int])
        self.assertEquals(nested_whiles(111, 114),
                          '...!...!...!...!...!')

    def test_poor_man_range(self):
        poor_man_range = self.make_cfunc(t.poor_man_range, [int])
        self.assertEquals(poor_man_range(10), range(10))

    def test_time_waster(self):
        time_waster = self.make_cfunc(t.time_waster, [int])
        self.assertEquals(time_waster(30), 3657)

if __name__ == '__main__':
    test.main()
