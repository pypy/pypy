import unittest
import support
import test_interpreter

class TestStdObjSpace(test_interpreter.TestInterpreter):

    def setUp(self):
        from pypy.objspace.std.objspace import StdObjSpace
        self.space = StdObjSpace()


if __name__ == '__main__':
    unittest.main()
