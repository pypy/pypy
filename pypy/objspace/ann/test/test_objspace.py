import autopath
from pypy.tool import test
from pypy.objspace.ann.objspace import W_Object, W_Anything, W_Integer
from pypy.objspace.ann.objspace import AnnotationObjSpace
from pypy.interpreter import baseobjspace, pyframe

class TestAnnotationObjSpace(test.TestCase):

    def codetest(self, source, functionname, args_w):
        """Compile and run the given code string, and then call its function
        named by 'functionname' with a list of wrapped arguments 'args_w'.
        Return the wrapped result."""

        glob = {}
        exec source in glob
        func = glob[functionname]

        w_args = self.space.newtuple(args_w)
        w_func = self.space.wrap(func)
        w_kwds = self.space.newdict([])
        return self.space.call(w_func, w_args, w_kwds)

    def setUp(self):
        self.space = AnnotationObjSpace()

    def test_any2any(self):
        x = self.codetest("def f(i):\n"
                          "    return i+1\n",
                           'f', [W_Anything()])
        self.assertEquals(type(x), W_Anything)

    def test_const2const(self):
        x = self.codetest("def f(i):\n"
                          "    return i+1\n",
                          'f', [self.space.wrap(5)])
        self.assertEquals(self.space.unwrap(x), 6)

    def test_constany2const(self):
        x = self.codetest("def f(i, j):\n"
                          "    return i+1\n",
                          'f', [self.space.wrap(5), W_Anything()])
        self.assertEquals(self.space.unwrap(x), 6)

    def test_int2int(self):
        x = self.codetest("def f(i):\n"
                          "    return i+1\n",
                          'f', [W_Integer()])
        self.assertEquals(type(x), W_Integer)

    def test_call(self):
        x = self.codetest("def f(i):\n"
                          "    return g(i)+2\n"
                          "def g(i):\n"
                          "     return i+1\n",
                          'f', [self.space.wrap(0)])
        self.assertEquals(self.space.unwrap(x), 3)

    def test_conditional_1(self):
        x = self.codetest("def f(i):\n"
                          "    if i < 0:\n"
                          "        return 0\n"
                          "    else:\n"
                          "        return 1\n",
                          'f', [W_Integer()])
        self.assertEquals(type(x), W_Integer)

    def test_conditional_2(self):
        x = self.codetest("def f(i):\n"
                          "    if i < 0:\n"
                          "        return 0\n"
                          "    else:\n"
                          "        return 0\n",
                          'f', [W_Integer()])
        self.assertEquals(self.space.unwrap(x), 0)

    def dont_test_while(self):
        x = self.codetest("def f(i):\n"
                          "    while i > 0:\n"
                          "        i = i-1\n"
                          "    return i\n",
                          'f', [W_Integer()])
        self.assertEquals(type(x), W_Integer)

    def dont_test_global(self):
        # XXX This doesn't work because we don't handle mutating globals
        x = self.codetest("def f(i, j):\n"
                          "    global x\n"
                          "    x = i\n"
                          "    if j > 0: pass\n"
                          "    g()\n"
                          "    return x\n"
                          "def g():\n"
                          "    global x\n"
                          "    x = x+1\n",
                          'f', [self.space.wrap(0), W_Anything()])
        self.assertEquals(self.space.unwrap(x), 1)



if __name__ == '__main__':
    test.main()
