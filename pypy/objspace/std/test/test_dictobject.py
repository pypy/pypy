import unittest, sys
import testsupport
from pypy.objspace.std import dictobject as dobj
from pypy.objspace.std.objspace import *


class TestW_DictObject(unittest.TestCase):

    def setUp(self):
        self.space = StdObjSpace()

    def tearDown(self):
        pass

    def test_empty(self):
        d = dobj.W_DictObject([])
        self.failIf(self.space.is_true(d))

if __name__ == '__main__':
    unittest.main()
