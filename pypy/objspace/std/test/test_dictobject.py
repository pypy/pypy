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
        space = self.space
        d = dobj.W_DictObject([])
        self.failIf(space.is_true(d))

    def test_nonempty(self):
        space = self.space
        wNone = space.w_None
        d = dobj.W_DictObject([(wNone, wNone)])
        self.failUnless(self.space.is_true(d))
        i = space.getitem(d, wNone)
        equal = space.eq(i, wNone)
        self.failUnless(space.is_true(equal))

if __name__ == '__main__':
    unittest.main()
