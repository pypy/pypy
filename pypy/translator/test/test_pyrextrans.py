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


def make_cfunc(func):
    """ make a pyrex-generated cfunction from the given func """
    import inspect
    try:
        func = func.im_func
    except AttributeError:
        pass
    from pypy.objspace.flow import Space
    space = Space()
    name = func.func_name
    funcgraph = space.build_flow(func)
    from pypy.translator.simplify import simplify_graph
    simplify_graph(funcgraph)
    funcgraph.source = inspect.getsource(func)
    result = GenPyrex(funcgraph).emitcode()
    make_dot(funcgraph, udir, 'ps')
    mod = make_module_from_pyxstring(name, udir, result)
    return getattr(mod, name)


from pypy.translator.test import snippet as t

class PyrexGenTestCase(test.IntTestCase):

    def setUp(self):
        self.space = test.objspace('flow')

    def test_simple_func(self):
        cfunc = make_cfunc(t.simple_func)
        self.assertEquals(cfunc(1), 2)

    def test_while_func(self):
        while_func = make_cfunc(t.while_func)
        self.assertEquals(while_func(10), 55)

    def test_nested_whiles(self):
        nested_whiles = make_cfunc(t.nested_whiles)
        self.assertEquals(nested_whiles(111, 114),
                          '...!...!...!...!...!')

    def test_poor_man_range(self):
        poor_man_range = make_cfunc(t.poor_man_range)
        self.assertEquals(poor_man_range(10), range(10))

    def test_simple_id(self):
        #we just want to see, if renaming of parameter works correctly
        #if the first branch is the end branch
        simple_id = make_cfunc(t.simple_id)
        self.assertEquals(simple_id(9), 9)

    def test_branch_id(self):
        branch_id = make_cfunc(t.branch_id)
        self.assertEquals(branch_id(1, 2, 3), 2)
        self.assertEquals(branch_id(0, 2, 3), 3)

    def dont_test_attrs(self):
        attrs = make_cfunc(t.attrs)
        self.assertEquals(attrs(), 9)

    def test_builtinusage(self):
        fun = make_cfunc(t.builtinusage)
        self.assertEquals(fun(), 4)

    def test_sieve(self):
        sieve = make_cfunc(t.sieve_of_eratosthenes)
        self.assertEquals(sieve(), 1028)

    def test_slice(self):
        half = make_cfunc(t.half_of_n)
        self.assertEquals(half(10), 5)

if __name__ == '__main__':
    test.main()
