import autopath
from pypy.tool import test

class TestFlowOjSpace(test.TestCase):
    def setUp(self):
        self.space = test.objspace('flow')

    def codetest(sefl, source, functionname, args_w):
        glob = {}
        exec source in glob
        func = glob[functionname]
        w_args = self.space.newtuple(args_w)
        w_func = self.space.wrap(func)
        w_kwds = self.space.newdict([])
        return self.space.build_flow(w_func, w_args, w_kwds)

    def test_nothing(self):
        x = self.codetest("def f():\n"
                          "    pass\n")
        self.assertEquals(len(x), 1)

    def test_ifthenelse(self):
        x = self.codetest("def f(i, j):\n"
                          "    if i < 0:\n"
                          "        i = j\n"
                          "    return g(i) + 1\n",
                          'f', [W_Anything()])
        self.assertEquals(x.graph_string(),
                          "")

if __name__ == '__main__':
    test.main()
