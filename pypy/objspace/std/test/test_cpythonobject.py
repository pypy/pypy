import unittest, sys, array
import testsupport
from pypy.objspace.std import cpythonobject
from pypy.objspace.std.objspace import *


class TestW_CPythonObject(unittest.TestCase):

    def setUp(self):
        self.space = StdObjSpace()
        self.stuff = array.array('b')  # arbitrary always-wrapped stuff

    def tearDown(self):
        pass

    def test_unary(self):
        for op, expected in [
            ('id',     id(self.stuff)),
            ('type',   array.ArrayType),
            ]:
            w1 = self.space.wrap(self.stuff)
            w_result = getattr(self.space, op)(w1)
            self.assertEquals(self.space.unwrap(w_result), expected)

if __name__ == '__main__':
    unittest.main()
