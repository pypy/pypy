import autopath
from pypy.tool import test
from pypy.objspace.ann.objspace import W_Object, W_Anything, W_Integer
from pypy.objspace.ann.objspace import AnnotationObjSpace
from pypy.interpreter import baseobjspace, executioncontext, pyframe

class TestAnnotationObjSpace(test.TestCase):

    def codetest(self, source, functionname, args_w):
        """Compile and run the given code string, and then call its function
        named by 'functionname' with a list of wrapped arguments 'args_w'.
        It returns the wrapped result."""

        glob = {}
        exec source in glob

        space = self.space
        w_args = space.newtuple(args_w)
        w_func = space.wrap(glob[functionname])
        w_kwds = space.newdict([])
        return space.call(w_func, w_args, w_kwds)

    def setUp(self):
        self.space = AnnotationObjSpace()

    def test_any2any(self):
        x = self.codetest('''
def f(i):
    return i+1
''', 'f', [W_Anything()])
        self.assertEquals(type(x), W_Anything)

    def test_const2const(self):
        x = self.codetest('''
def f(i):
    return i+1
''', 'f', [self.space.wrap(5)])
        self.assertEquals(self.space.unwrap(x), 6)

    def test_constany2const(self):
        x = self.codetest('''
def f(i, j):
    return i+1
''', 'f', [self.space.wrap(5), W_Anything()])
        self.assertEquals(self.space.unwrap(x), 6)

    def test_int2int(self):
        x = self.codetest('''
def f(i):
    return i+1
''', 'f', [W_Integer()])
        self.assertEquals(type(x), W_Integer)



if __name__ == '__main__':
    test.main()
