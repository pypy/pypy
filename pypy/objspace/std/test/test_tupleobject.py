import unittest, sys
import testsupport
from pypy.interpreter import unittest_w
from pypy.objspace.std import tupleobject as tobj
from pypy.objspace.std.objspace import *


class TestW_TupleObject(unittest_w.TestCase_w):

    def setUp(self):
        self.space = StdObjSpace()

    def tearDown(self):
        pass

    def test_is_true(self):
        w = self.space.wrap
        w_tuple = tobj.W_TupleObject([])
        self.assertEqual(self.space.is_true(w_tuple), False)
        w_tuple = tobj.W_TupleObject([w(5)])
        self.assertEqual(self.space.is_true(w_tuple), True)
        w_tuple = tobj.W_TupleObject([w(5), w(3)])
        self.assertEqual(self.space.is_true(w_tuple), True)

    def test_getitem(self):
        w = self.space.wrap
        w_tuple = tobj.W_TupleObject([w(5), w(3)])
        self.assertEqual_w(self.space.getitem(w_tuple, w(0)), w(5))
        self.assertEqual_w(self.space.getitem(w_tuple, w(1)), w(3))
        self.assertEqual_w(self.space.getitem(w_tuple, w(-2)), w(5))
        self.assertEqual_w(self.space.getitem(w_tuple, w(-1)), w(3))
        self.assertRaises_w(self.space.w_IndexError,
                            self.space.getitem, w_tuple, w(2))
        self.assertRaises_w(self.space.w_IndexError,
                            self.space.getitem, w_tuple, w(42))
        self.assertRaises_w(self.space.w_IndexError,
                            self.space.getitem, w_tuple, w(-3))

    def test_iter(self):
        w = self.space.wrap
        w_tuple = tobj.W_TupleObject([w(5), w(3), w(99)])
        w_iter = self.space.iter(w_tuple)
        self.assertEqual_w(self.space.next(w_iter), w(5))
        self.assertEqual_w(self.space.next(w_iter), w(3))
        self.assertEqual_w(self.space.next(w_iter), w(99))
        self.assertRaises(NoValue, self.space.next, w_iter)
        self.assertRaises(NoValue, self.space.next, w_iter)

if __name__ == '__main__':
    unittest.main()
