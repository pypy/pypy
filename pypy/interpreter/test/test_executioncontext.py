import testsupport

from pypy.interpreter.pyframe import PyFrame
from pypy.interpreter import baseobjspace, executioncontext


class TestExecutionContext(testsupport.TestCase):

    def test_trivial1(self):
        # build frame
        space = testsupport.objspace()
        ec = executioncontext.ExecutionContext(space)
        compile = space.builtin.compile
        bytecode = compile(space.wrap('def f(x): return x+1'),
                           space.wrap('<string>'),
                           space.wrap('exec')).co_consts[0]
        w_globals = ec.make_standard_w_globals()
        w_locals = space.newdict([(space.wrap('x'), space.wrap(5))])
        frame = PyFrame(space, bytecode, w_globals, w_locals)
        w_output = ec.eval_frame(frame)
        self.assertEquals(frame.space.unwrap(w_output), 6)


if __name__ == '__main__':
    testsupport.main()
