#from __future__ import nested_scopes
import autopath
from pypy.objspace.std.listobject import W_ListObject
from pypy.objspace.std.objspace import NoValue
from pypy.tool import test


class TestW_ListObject(test.TestCase):

    def setUp(self):
        self.space = test.objspace('std')

    def tearDown(self):
        pass

    def test_is_true(self):
        w = self.space.wrap
        w_list = W_ListObject(self.space, [])
        self.assertEqual(self.space.is_true(w_list), False)
        w_list = W_ListObject(self.space, [w(5)])
        self.assertEqual(self.space.is_true(w_list), True)
        w_list = W_ListObject(self.space, [w(5), w(3)])
        self.assertEqual(self.space.is_true(w_list), True)

    def test_len(self):
        w = self.space.wrap
        w_list = W_ListObject(self.space, [])
        self.assertEqual_w(self.space.len(w_list), w(0))
        w_list = W_ListObject(self.space, [w(5)])
        self.assertEqual_w(self.space.len(w_list), w(1))
        w_list = W_ListObject(self.space, [w(5), w(3), w(99)]*111)
        self.assertEqual_w(self.space.len(w_list), w(333))
 
    def test_getitem(self):
        w = self.space.wrap
        w_list = W_ListObject(self.space, [w(5), w(3)])
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
        w_list = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_iter = self.space.iter(w_list)
        self.assertEqual_w(self.space.next(w_iter), w(5))
        self.assertEqual_w(self.space.next(w_iter), w(3))
        self.assertEqual_w(self.space.next(w_iter), w(99))
        self.assertRaises(NoValue, self.space.next, w_iter)
        self.assertRaises(NoValue, self.space.next, w_iter)

    def test_contains(self):
        w = self.space.wrap
        w_list = W_ListObject(self.space, [w(5), w(3), w(99)])
        self.assertEqual_w(self.space.contains(w_list, w(5)),
                           self.space.w_True)
        self.assertEqual_w(self.space.contains(w_list, w(99)),
                           self.space.w_True)
        self.assertEqual_w(self.space.contains(w_list, w(11)),
                           self.space.w_False)
        self.assertEqual_w(self.space.contains(w_list, w_list),
                           self.space.w_False)

    def test_getslice(self):
        w = self.space.wrap

        def test1(testlist, start, stop, step, expected):
            w_slice  = self.space.newslice(w(start), w(stop), w(step))
            w_list = W_ListObject(self.space, [w(i) for i in testlist])
            w_result = self.space.getitem(w_list, w_slice)
            self.assertEqual(self.space.unwrap(w_result), expected)
        
        for testlist in [[], [5,3,99]]:
            for start in [-2, 0, 1, 10]:
                for end in [-1, 2, 999]:
                    test1(testlist, start, end, 1, testlist[start:end])

        test1([5,7,1,4], 3, 1, -2,  [4,])
        test1([5,7,1,4], 3, 0, -2,  [4, 7])
        test1([5,7,1,4], 3, -1, -2, [])
        test1([5,7,1,4], -2, 11, 2, [1,])
        test1([5,7,1,4], -3, 11, 2, [7, 4])
        test1([5,7,1,4], -5, 11, 2, [5, 1])

    def test_setslice(self):
        w = self.space.wrap

        def test1(lhslist, start, stop, rhslist, expected):
            w_slice  = self.space.newslice(w(start), w(stop), w(1))
            w_lhslist = W_ListObject(self.space, [w(i) for i in lhslist])
            w_rhslist = W_ListObject(self.space, [w(i) for i in rhslist])
            self.space.setitem(w_lhslist, w_slice, w_rhslist)
            self.assertEqual(self.space.unwrap(w_lhslist), expected)
        

        test1([5,7,1,4], 1, 3, [9,8],  [5,9,8,4])
        test1([5,7,1,4], 1, 3, [9],    [5,9,4])
        test1([5,7,1,4], 1, 3, [9,8,6],[5,9,8,6,4])
        test1([5,7,1,4], 1, 3, [],     [5,4])
        test1([5,7,1,4], 2, 2, [9],    [5,7,9,1,4])
        test1([5,7,1,4], 0, 99,[9,8],  [9,8])

    def test_add(self):
        w = self.space.wrap
        w_list0 = W_ListObject(self.space, [])
        w_list1 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list2 = W_ListObject(self.space, [w(-7)] * 111)
        self.assertEqual_w(self.space.add(w_list1, w_list1),
                           W_ListObject(self.space, [w(5), w(3), w(99),
                                               w(5), w(3), w(99)]))
        self.assertEqual_w(self.space.add(w_list1, w_list2),
                           W_ListObject(self.space, [w(5), w(3), w(99)] +
                                              [w(-7)] * 111))
        self.assertEqual_w(self.space.add(w_list1, w_list0), w_list1)
        self.assertEqual_w(self.space.add(w_list0, w_list2), w_list2)

    def test_mul(self):
        # only testing right mul at the moment
        w = self.space.wrap
        arg = w(2)
        n = 3
        w_lis = W_ListObject(self.space, [arg])
        w_lis3 = W_ListObject(self.space, [arg]*n)
        w_res = self.space.mul(w_lis, w(n))
        self.assertEqual_w(w_lis3, w_res)
        # commute
        w_res = self.space.mul(w(n), w_lis)
        self.assertEqual_w(w_lis3, w_res)

    def test_setitem(self):
        w = self.space.wrap
        w_list = W_ListObject(self.space, [w(5), w(3)])
        w_exp1 = W_ListObject(self.space, [w(5), w(7)])
        w_exp2 = W_ListObject(self.space, [w(8), w(7)])
        self.space.setitem(w_list, w(1), w(7))
        self.assertEqual_w(w_exp1, w_list)
        self.space.setitem(w_list, w(-2), w(8))
        self.assertEqual_w(w_exp2, w_list)
        self.assertRaises_w(self.space.w_IndexError,
                            self.space.setitem, w_list, w(2), w(5))
        self.assertRaises_w(self.space.w_IndexError,
                            self.space.setitem, w_list, w(-3), w(5))

    def test_eq(self):
        w = self.space.wrap
        
        w_list0 = W_ListObject(self.space, [])
        w_list1 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list2 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list3 = W_ListObject(self.space, [w(5), w(3), w(99), w(-1)])

        self.assertEqual_w(self.space.eq(w_list0, w_list1),
                           self.space.w_False)
        self.assertEqual_w(self.space.eq(w_list1, w_list0),
                           self.space.w_False)
        self.assertEqual_w(self.space.eq(w_list1, w_list1),
                           self.space.w_True)
        self.assertEqual_w(self.space.eq(w_list1, w_list2),
                           self.space.w_True)
        self.assertEqual_w(self.space.eq(w_list2, w_list3),
                           self.space.w_False)
    def test_ne(self):
        w = self.space.wrap
        
        w_list0 = W_ListObject(self.space, [])
        w_list1 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list2 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list3 = W_ListObject(self.space, [w(5), w(3), w(99), w(-1)])

        self.assertEqual_w(self.space.ne(w_list0, w_list1),
                           self.space.w_True)
        self.assertEqual_w(self.space.ne(w_list1, w_list0),
                           self.space.w_True)
        self.assertEqual_w(self.space.ne(w_list1, w_list1),
                           self.space.w_False)
        self.assertEqual_w(self.space.ne(w_list1, w_list2),
                           self.space.w_False)
        self.assertEqual_w(self.space.ne(w_list2, w_list3),
                           self.space.w_True)
    def test_lt(self):
        w = self.space.wrap
        
        w_list0 = W_ListObject(self.space, [])
        w_list1 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list2 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list3 = W_ListObject(self.space, [w(5), w(3), w(99), w(-1)])
        w_list4 = W_ListObject(self.space, [w(5), w(3), w(9), w(-1)])

        self.assertEqual_w(self.space.lt(w_list0, w_list1),
                           self.space.w_True)
        self.assertEqual_w(self.space.lt(w_list1, w_list0),
                           self.space.w_False)
        self.assertEqual_w(self.space.lt(w_list1, w_list1),
                           self.space.w_False)
        self.assertEqual_w(self.space.lt(w_list1, w_list2),
                           self.space.w_False)
        self.assertEqual_w(self.space.lt(w_list2, w_list3),
                           self.space.w_True)
        self.assertEqual_w(self.space.lt(w_list4, w_list3),
                           self.space.w_True)
        
    def test_ge(self):
        w = self.space.wrap
        
        w_list0 = W_ListObject(self.space, [])
        w_list1 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list2 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list3 = W_ListObject(self.space, [w(5), w(3), w(99), w(-1)])
        w_list4 = W_ListObject(self.space, [w(5), w(3), w(9), w(-1)])

        self.assertEqual_w(self.space.ge(w_list0, w_list1),
                           self.space.w_False)
        self.assertEqual_w(self.space.ge(w_list1, w_list0),
                           self.space.w_True)
        self.assertEqual_w(self.space.ge(w_list1, w_list1),
                           self.space.w_True)
        self.assertEqual_w(self.space.ge(w_list1, w_list2),
                           self.space.w_True)
        self.assertEqual_w(self.space.ge(w_list2, w_list3),
                           self.space.w_False)
        self.assertEqual_w(self.space.ge(w_list4, w_list3),
                           self.space.w_False)
        
    def test_gt(self):
        w = self.space.wrap
        
        w_list0 = W_ListObject(self.space, [])
        w_list1 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list2 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list3 = W_ListObject(self.space, [w(5), w(3), w(99), w(-1)])
        w_list4 = W_ListObject(self.space, [w(5), w(3), w(9), w(-1)])

        self.assertEqual_w(self.space.gt(w_list0, w_list1),
                           self.space.w_False)
        self.assertEqual_w(self.space.gt(w_list1, w_list0),
                           self.space.w_True)
        self.assertEqual_w(self.space.gt(w_list1, w_list1),
                           self.space.w_False)
        self.assertEqual_w(self.space.gt(w_list1, w_list2),
                           self.space.w_False)
        self.assertEqual_w(self.space.gt(w_list2, w_list3),
                           self.space.w_False)
        self.assertEqual_w(self.space.gt(w_list4, w_list3),
                           self.space.w_False)
        
    def test_le(self):
        w = self.space.wrap
        
        w_list0 = W_ListObject(self.space, [])
        w_list1 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list2 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list3 = W_ListObject(self.space, [w(5), w(3), w(99), w(-1)])
        w_list4 = W_ListObject(self.space, [w(5), w(3), w(9), w(-1)])

        self.assertEqual_w(self.space.le(w_list0, w_list1),
                           self.space.w_True)
        self.assertEqual_w(self.space.le(w_list1, w_list0),
                           self.space.w_False)
        self.assertEqual_w(self.space.le(w_list1, w_list1),
                           self.space.w_True)
        self.assertEqual_w(self.space.le(w_list1, w_list2),
                           self.space.w_True)
        self.assertEqual_w(self.space.le(w_list2, w_list3),
                           self.space.w_True)
        self.assertEqual_w(self.space.le(w_list4, w_list3),
                           self.space.w_True)

class AppTestW_ListObject(test.AppTestCase):
    def setUp(self):
        self.space = test.objspace('std')

    def test_explicit_new_init(self):
        l = list.__new__(list)
        l.__init__([1,2])
        self.assertEquals(l,[1,2])
        list.__init__(l,[1,2,3])
        self.assertEquals(l,[1,2,3])
        
    def test_extend_list(self):
        l = [1]
        l.extend([2])
        self.assertEquals(l, [1,2])

    def test_extend_tuple(self):
        l = [1]
        l.extend((2,))
        self.assertEquals(l, [1,2])

    def test_extended_slice(self):
        l = range(10)
        del l[::2]
        self.assertEquals(l,[1,3,5,7,9])
        l[-2::-1] = l[:-1]
        self.assertEquals(l,[7,5,3,1,9])
        del l[-1:2:-1]
        self.assertEquals(l,[7,5,3])
        del l[:2]
        self.assertEquals(l,[3])
        
if __name__ == '__main__':
    test.main()
