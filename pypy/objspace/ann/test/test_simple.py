import autopath
from pypy.tool import test
from pypy.objspace.ann.objspace import W_Object, W_Anything, AnnotationObjSpace
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

    def test_simple1(self):
        x = self.codetest('''
def f(i):
    return i+1
''', 'f', [W_Anything()])
        self.assert_(isinstance(x, W_Anything))


if __name__ == '__main__':
    test.main()
