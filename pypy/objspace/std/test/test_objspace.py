import unittest, sys
import testsupport
from pypy.interpreter import unittest_w
from pypy.objspace.std import noneobject as nobj
from pypy.objspace.std.objspace import *


class TestStdObjectSpace(unittest_w.TestCase_w):

    def setUp(self):
        self.space = StdObjSpace()

    def tearDown(self):
        pass

    def test_newstring(self):
        w = self.space.wrap
        s = 'abc'
        chars_w = [w(ord(c)) for c in s]
        self.assertEqual_w(w(s), self.space.newstring(chars_w))

    def test_newstring_fail(self):
        w = self.space.wrap
        s = 'abc'
        not_chars_w = [w(c) for c in s]
        self.assertRaises_w(self.space.w_TypeError,
                            self.space.newstring,
                            not_chars_w)
        self.assertRaises_w(self.space.w_ValueError,
                            self.space.newstring,
                            [w(-1)])

if __name__ == '__main__':
    unittest.main()
