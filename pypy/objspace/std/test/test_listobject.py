from __future__ import nested_scopes
import unittest, sys
import testsupport
from pypy.interpreter import unittest_w
from pypy.objspace.std import listobject as tobj
from pypy.objspace.std.objspace import *


class TestW_ListObject(unittest_w.TestCase_w):

    def setUp(self):
        self.space = StdObjSpace()

    def tearDown(self):
        pass

    def test_is_true(self):
        w = self.space.wrap
        w_list = tobj.W_ListObject(self.space, [])
        self.assertEqual(self.space.is_true(w_list), False)
        w_list = tobj.W_ListObject(self.space, [w(5)])
        self.assertEqual(self.space.is_true(w_list), True)
        w_list = tobj.W_ListObject(self.space, [w(5), w(3)])
        self.assertEqual(self.space.is_true(w_list), True)

    def test_len(self):
        w = self.space.wrap
        w_list = tobj.W_ListObject(self.space, [])
        self.assertEqual_w(self.space.len(w_list), w(0))
        w_list = tobj.W_ListObject(self.space, [w(5)])
        self.assertEqual_w(self.space.len(w_list), w(1))
        w_list = tobj.W_ListObject(self.space, [w(5), w(3), w(99)]*111)
        self.assertEqual_w(self.space.len(w_list), w(333))

    def test_mul(self):
        # only testing right mul at the moment
        w = self.space.wrap
        arg = w(2)
        n = 3
        w_lis = tobj.W_ListObject(self.space, [arg])
        w_lis3 = tobj.W_ListObject(self.space, [arg]*n)
        w_res = self.space.mul(w_lis, w(n))
        self.assertEqual_w(w_lis3, w_res)

    def test_getitem(self):
        w = self.space.wrap
        w_list = tobj.W_ListObject(self.space, [w(5), w(3)])
        self.assertEqual_w(self.space.getitem(w_list, w(0)), w(5))
        self.assertEqual_w(self.space.getitem(w_list, w(1)), w(3))
        self.assertEqual_w(self.space.getitem(w_list, w(-2)), w(5))
        self.assertEqual_w(self.space.getitem(w_list, w(-1)), w(3))
        self.assertRaises_w(self.space.w_IndexError,
                            self.space.getitem, w_list, w(2))
        self.assertRaises_w(self.space.w_IndexError,
                            self.space.getitem, w_list, w(42))
        self.assertRaises_w(self.space.w_IndexError,
                            self.space.getitem, w_list, w(-3))

    def test_iter(self):
        w = self.space.wrap
        w_list = tobj.W_ListObject(self.space, [w(5), w(3), w(99)])
        w_iter = self.space.iter(w_list)
        self.assertEqual_w(self.space.next(w_iter), w(5))
        self.assertEqual_w(self.space.next(w_iter), w(3))
        self.assertEqual_w(self.space.next(w_iter), w(99))
        self.assertRaises(NoValue, self.space.next, w_iter)
        self.assertRaises(NoValue, self.space.next, w_iter)

    def test_add(self):
        w = self.space.wrap
        w_list0 = tobj.W_ListObject(self.space, [])
        w_list1 = tobj.W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list2 = tobj.W_ListObject(self.space, [w(-7)] * 111)
        self.assertEqual_w(self.space.add(w_list1, w_list1),
                           tobj.W_ListObject(self.space, [w(5), w(3), w(99),
                                                          w(5), w(3), w(99)]))
        self.assertEqual_w(self.space.add(w_list1, w_list2),
                           tobj.W_ListObject(self.space, [w(5), w(3), w(99)] +
                                             [w(-7)] * 111))
        self.assertEqual_w(self.space.add(w_list1, w_list0), w_list1)
        self.assertEqual_w(self.space.add(w_list0, w_list2), w_list2)

    def test_getslice(self):
        w = self.space.wrap

        def test1(testlist, start, stop, step, expected):
            w_slice  = self.space.newslice(w(start), w(stop), w(step))
            w_list = tobj.W_ListObject(self.space, [w(i) for i in testlist])
            w_result = self.space.getitem(w_list, w_slice)
            self.assertEqual(self.space.unwrap(w_result), expected)
        
        for testlist in [[], [5,3,99], list(range(5,555,10))]:
            for start in [-2, -1, 0, 1, 10]:
                for end in [-1, 0, 2, 999]:
                    test1(testlist, start, end, 1, testlist[start:end])

        test1([5,7,1,4], 3, 1, -2,  [4,])
        test1([5,7,1,4], 3, 0, -2,  [4, 7])
        test1([5,7,1,4], 3, -1, -2, [])
        test1([5,7,1,4], -2, 11, 2, [1])
        test1([5,7,1,4], -3, 11, 2, [7, 4])
        test1([5,7,1,4], -5, 11, 2, [5, 1])

if __name__ == '__main__':
    unittest.main()
