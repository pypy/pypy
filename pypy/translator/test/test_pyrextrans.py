import autopath
from pypy.tool import test
from pypy.tool.udir import udir
from pypy.translator.genpyrex import GenPyrex
from pypy.translator.flowmodel import *
from pypy.translator.test.buildpyxmodule import make_module_from_pyxstring

make_dot = True

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

class PyrexGenTestCase(test.IntTestCase):
    def setUp(self):
        self.space = test.objspace('flow')

    #____________________________________________________
    def simple_func(i):
        return i+1

    def test_simple_func(self):
        cfunc = make_cfunc(self.simple_func)
        self.assertEquals(cfunc(1), 2)

    #____________________________________________________
    def while_func(i):
        total = 0
        while i > 0:
            total = total + i
            i = i - 1
        return total

    def test_while_func(self):
        while_func = make_cfunc(self.while_func)
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
        nested_whiles = make_cfunc(self.nested_whiles)
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
        poor_man_range = make_cfunc(self.poor_man_range)
        self.assertEquals(poor_man_range(10), range(10))

   #____________________________________________________

    def simple_id(x):
        return x

    def test_simple_id(self):
        #we just want to see, if renaming of parameter works correctly
        #if the first branch is the end branch
        simple_id = make_cfunc(self.simple_id)
        self.assertEquals(simple_id(9), 9)

   #____________________________________________________

    def branch_id(cond, a, b):
        while 1:
            if cond:
                return a
            else:
                return b

    def test_branch_id(self):
        branch_id = make_cfunc(self.branch_id)
        self.assertEquals(branch_id(1, 2, 3), 2)
        self.assertEquals(branch_id(0, 2, 3), 3)

    #____________________________________________________

    def attrs():
        def b(): pass
        b.f = 4
        b.g = 5

        return b.f + b.g

    def _test_attrs(self):
        attrs = make_cfunc(self.attrs)
        self.assertEquals(attrs(), 9)

    #_____________________________________________________

    def builtinusage():
        return pow(2,2)

    def test_builtinusage(self):
        fun = make_cfunc(self.builtinusage)
        self.assertEquals(fun(), 4)

    #_____________________________________________________
    def sieve_of_eratosthenes():
        # This one is from:
        # The Great Computer Language Shootout
        flags = [True] * (8192+1)
        count = 0
        i = 2
        while i <= 8192:
            if flags[i]:
                k = i + i
                while k <= 8192:
                    flags[k] = False
                    k = k + i
                count = count + 1
            i = i + 1
        return count

    def test_sieve(self):
        sieve = make_cfunc(self.sieve_of_eratosthenes)
        self.assertEquals(sieve(), 1028)

if __name__ == '__main__':
    test.main()
