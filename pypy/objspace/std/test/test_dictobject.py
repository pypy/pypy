import unittest, sys
import testsupport
from pypy.objspace.std import dictobject as dobj
from pypy.objspace.std.objspace import *


class TestW_DictObject(testsupport.TestCase_w):

    def setUp(self):
        self.space = StdObjSpace()

    def tearDown(self):
        pass

    def test_empty(self):
        space = self.space
        d = dobj.W_DictObject([])
        self.failIf_w(d)

    def test_nonempty(self):
        space = self.space
        wNone = space.w_None
        d = dobj.W_DictObject([(wNone, wNone)])
        self.failUnless(self.space.is_true(d))
        i = space.getitem(d, wNone)
        equal = space.eq(i, wNone)
        self.failUnless(space.is_true(equal))

    def test_setitem(self):
        space = self.space
        wk1 = space.wrap('key')
        wone = space.wrap(1)
        d = dobj.W_DictObject([(space.wrap('zero'),space.wrap(0))])
        space.setitem(d,wk1,wone)
        wback = space.getitem(d,wk1)
        self.assertEqual_w(wback,wone)

if __name__ == '__main__':
    unittest.main()
