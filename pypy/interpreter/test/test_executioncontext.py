import autopath

from pypy.tool import test
from pypy.interpreter import baseobjspace, executioncontext



class TestExecutionContext(test.TestCase):

    #
    # XXX not sure what specifically this class used to test
    # XXX turn this into a proper unit test
    #
    pass

##    def test_trivial1(self):
##        # build frame
##        space = test.objspace()
##        ec = executioncontext.ExecutionContext(space)
##        compile = space.builtin.compile
##        bytecode = space.unwrap(compile(space.wrap('def f(x): return x+1'),
##                                        space.wrap('<string>'),
##                                        space.wrap('exec'))).co_consts[0]
##        w_globals = ec.make_standard_w_globals()
##        w_locals = space.newdict([(space.wrap('x'), space.wrap(5))])
##        scopedcode = ScopedCode(space, bytecode, w_globals)
##        w_output = scopedcode.eval_frame(w_locals)
##        self.assertEquals(space.unwrap(w_output), 6)


if __name__ == '__main__':
    test.main()
