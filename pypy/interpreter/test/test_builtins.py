import unittest, sys, os
sys.path.insert(0, '..')

from pyframe import PyFrame
import pypy.objspace.trivial as trivialspace

def make_builtins_global():
        d = {}
        exec '''def filter(a, b): return 42''' in d 
        return d

class TestBuiltins(unittest.TestCase):

    def test_filter_None(self):
        # build frame
        space = trivialspace
        bytecode = compile("def f(x): return filter(None, [1, '', 2])", '', 'exec').co_consts[0]
        d = make_builtins_global()
        w_globals = space.wrap(d)
        w_locals = space.wrap({})
        frame = PyFrame(space, bytecode, w_globals, w_locals)

        # perform call
        w_input = frame.space.wrap((5,))
        frame.setargs(w_input)
        w_output = frame.eval()
        self.assertEquals(frame.space.unwrap(w_output), [1,2])
        

if __name__ == '__main__':
    unittest.main()
