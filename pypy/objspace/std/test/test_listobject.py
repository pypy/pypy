#from __future__ import nested_scopes
import autopath
from pypy.objspace.std.listobject import W_ListObject
from pypy.interpreter.error import OperationError


objspacename = 'std'

class TestW_ListObject:

    def test_is_true(self):
        w = self.space.wrap
        w_list = W_ListObject(self.space, [])
        assert self.space.is_true(w_list) == False
        w_list = W_ListObject(self.space, [w(5)])
        assert self.space.is_true(w_list) == True
        w_list = W_ListObject(self.space, [w(5), w(3)])
        assert self.space.is_true(w_list) == True

    def test_len(self):
        w = self.space.wrap
        w_list = W_ListObject(self.space, [])
        assert self.space.eq_w(self.space.len(w_list), w(0))
        w_list = W_ListObject(self.space, [w(5)])
        assert self.space.eq_w(self.space.len(w_list), w(1))
        w_list = W_ListObject(self.space, [w(5), w(3), w(99)]*111)
        assert self.space.eq_w(self.space.len(w_list), w(333))
 
    def test_getitem(self):
        w = self.space.wrap
        w_list = W_ListObject(self.space, [w(5), w(3)])
        assert self.space.eq_w(self.space.getitem(w_list, w(0)), w(5))
        assert self.space.eq_w(self.space.getitem(w_list, w(1)), w(3))
        assert self.space.eq_w(self.space.getitem(w_list, w(-2)), w(5))
        assert self.space.eq_w(self.space.getitem(w_list, w(-1)), w(3))
        self.space.raises_w(self.space.w_IndexError,
                            self.space.getitem, w_list, w(2))
        self.space.raises_w(self.space.w_IndexError,
                            self.space.getitem, w_list, w(42))
        self.space.raises_w(self.space.w_IndexError,
                            self.space.getitem, w_list, w(-3))

    def test_iter(self):
        w = self.space.wrap
        w_list = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_iter = self.space.iter(w_list)
        assert self.space.eq_w(self.space.next(w_iter), w(5))
        assert self.space.eq_w(self.space.next(w_iter), w(3))
        assert self.space.eq_w(self.space.next(w_iter), w(99))
        raises(OperationError, self.space.next, w_iter)
        raises(OperationError, self.space.next, w_iter)

    def test_contains(self):
        w = self.space.wrap
        w_list = W_ListObject(self.space, [w(5), w(3), w(99)])
        assert self.space.eq_w(self.space.contains(w_list, w(5)),
                           self.space.w_True)
        assert self.space.eq_w(self.space.contains(w_list, w(99)),
                           self.space.w_True)
        assert self.space.eq_w(self.space.contains(w_list, w(11)),
                           self.space.w_False)
        assert self.space.eq_w(self.space.contains(w_list, w_list),
                           self.space.w_False)

    def test_getslice(self):
        w = self.space.wrap

        def test1(testlist, start, stop, step, expected):
            w_slice  = self.space.newslice(w(start), w(stop), w(step))
            w_list = W_ListObject(self.space, [w(i) for i in testlist])
            w_result = self.space.getitem(w_list, w_slice)
            assert self.space.unwrap(w_result) == expected
        
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
            assert self.space.unwrap(w_lhslist) == expected
        

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
        assert self.space.eq_w(self.space.add(w_list1, w_list1),
                           W_ListObject(self.space, [w(5), w(3), w(99),
                                               w(5), w(3), w(99)]))
        assert self.space.eq_w(self.space.add(w_list1, w_list2),
                           W_ListObject(self.space, [w(5), w(3), w(99)] +
                                              [w(-7)] * 111))
        assert self.space.eq_w(self.space.add(w_list1, w_list0), w_list1)
        assert self.space.eq_w(self.space.add(w_list0, w_list2), w_list2)

    def test_mul(self):
        # only testing right mul at the moment
        w = self.space.wrap
        arg = w(2)
        n = 3
        w_lis = W_ListObject(self.space, [arg])
        w_lis3 = W_ListObject(self.space, [arg]*n)
        w_res = self.space.mul(w_lis, w(n))
        assert self.space.eq_w(w_lis3, w_res)
        # commute
        w_res = self.space.mul(w(n), w_lis)
        assert self.space.eq_w(w_lis3, w_res)

    def test_setitem(self):
        w = self.space.wrap
        w_list = W_ListObject(self.space, [w(5), w(3)])
        w_exp1 = W_ListObject(self.space, [w(5), w(7)])
        w_exp2 = W_ListObject(self.space, [w(8), w(7)])
        self.space.setitem(w_list, w(1), w(7))
        assert self.space.eq_w(w_exp1, w_list)
        self.space.setitem(w_list, w(-2), w(8))
        assert self.space.eq_w(w_exp2, w_list)
        self.space.raises_w(self.space.w_IndexError,
                            self.space.setitem, w_list, w(2), w(5))
        self.space.raises_w(self.space.w_IndexError,
                            self.space.setitem, w_list, w(-3), w(5))

    def test_eq(self):
        w = self.space.wrap
        
        w_list0 = W_ListObject(self.space, [])
        w_list1 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list2 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list3 = W_ListObject(self.space, [w(5), w(3), w(99), w(-1)])

        assert self.space.eq_w(self.space.eq(w_list0, w_list1),
                           self.space.w_False)
        assert self.space.eq_w(self.space.eq(w_list1, w_list0),
                           self.space.w_False)
        assert self.space.eq_w(self.space.eq(w_list1, w_list1),
                           self.space.w_True)
        assert self.space.eq_w(self.space.eq(w_list1, w_list2),
                           self.space.w_True)
        assert self.space.eq_w(self.space.eq(w_list2, w_list3),
                           self.space.w_False)
    def test_ne(self):
        w = self.space.wrap
        
        w_list0 = W_ListObject(self.space, [])
        w_list1 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list2 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list3 = W_ListObject(self.space, [w(5), w(3), w(99), w(-1)])

        assert self.space.eq_w(self.space.ne(w_list0, w_list1),
                           self.space.w_True)
        assert self.space.eq_w(self.space.ne(w_list1, w_list0),
                           self.space.w_True)
        assert self.space.eq_w(self.space.ne(w_list1, w_list1),
                           self.space.w_False)
        assert self.space.eq_w(self.space.ne(w_list1, w_list2),
                           self.space.w_False)
        assert self.space.eq_w(self.space.ne(w_list2, w_list3),
                           self.space.w_True)
    def test_lt(self):
        w = self.space.wrap
        
        w_list0 = W_ListObject(self.space, [])
        w_list1 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list2 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list3 = W_ListObject(self.space, [w(5), w(3), w(99), w(-1)])
        w_list4 = W_ListObject(self.space, [w(5), w(3), w(9), w(-1)])

        assert self.space.eq_w(self.space.lt(w_list0, w_list1),
                           self.space.w_True)
        assert self.space.eq_w(self.space.lt(w_list1, w_list0),
                           self.space.w_False)
        assert self.space.eq_w(self.space.lt(w_list1, w_list1),
                           self.space.w_False)
        assert self.space.eq_w(self.space.lt(w_list1, w_list2),
                           self.space.w_False)
        assert self.space.eq_w(self.space.lt(w_list2, w_list3),
                           self.space.w_True)
        assert self.space.eq_w(self.space.lt(w_list4, w_list3),
                           self.space.w_True)
        
    def test_ge(self):
        w = self.space.wrap
        
        w_list0 = W_ListObject(self.space, [])
        w_list1 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list2 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list3 = W_ListObject(self.space, [w(5), w(3), w(99), w(-1)])
        w_list4 = W_ListObject(self.space, [w(5), w(3), w(9), w(-1)])

        assert self.space.eq_w(self.space.ge(w_list0, w_list1),
                           self.space.w_False)
        assert self.space.eq_w(self.space.ge(w_list1, w_list0),
                           self.space.w_True)
        assert self.space.eq_w(self.space.ge(w_list1, w_list1),
                           self.space.w_True)
        assert self.space.eq_w(self.space.ge(w_list1, w_list2),
                           self.space.w_True)
        assert self.space.eq_w(self.space.ge(w_list2, w_list3),
                           self.space.w_False)
        assert self.space.eq_w(self.space.ge(w_list4, w_list3),
                           self.space.w_False)
        
    def test_gt(self):
        w = self.space.wrap
        
        w_list0 = W_ListObject(self.space, [])
        w_list1 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list2 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list3 = W_ListObject(self.space, [w(5), w(3), w(99), w(-1)])
        w_list4 = W_ListObject(self.space, [w(5), w(3), w(9), w(-1)])

        assert self.space.eq_w(self.space.gt(w_list0, w_list1),
                           self.space.w_False)
        assert self.space.eq_w(self.space.gt(w_list1, w_list0),
                           self.space.w_True)
        assert self.space.eq_w(self.space.gt(w_list1, w_list1),
                           self.space.w_False)
        assert self.space.eq_w(self.space.gt(w_list1, w_list2),
                           self.space.w_False)
        assert self.space.eq_w(self.space.gt(w_list2, w_list3),
                           self.space.w_False)
        assert self.space.eq_w(self.space.gt(w_list4, w_list3),
                           self.space.w_False)
        
    def test_le(self):
        w = self.space.wrap
        
        w_list0 = W_ListObject(self.space, [])
        w_list1 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list2 = W_ListObject(self.space, [w(5), w(3), w(99)])
        w_list3 = W_ListObject(self.space, [w(5), w(3), w(99), w(-1)])
        w_list4 = W_ListObject(self.space, [w(5), w(3), w(9), w(-1)])

        assert self.space.eq_w(self.space.le(w_list0, w_list1),
                           self.space.w_True)
        assert self.space.eq_w(self.space.le(w_list1, w_list0),
                           self.space.w_False)
        assert self.space.eq_w(self.space.le(w_list1, w_list1),
                           self.space.w_True)
        assert self.space.eq_w(self.space.le(w_list1, w_list2),
                           self.space.w_True)
        assert self.space.eq_w(self.space.le(w_list2, w_list3),
                           self.space.w_True)
        assert self.space.eq_w(self.space.le(w_list4, w_list3),
                           self.space.w_True)

class AppTestW_ListObject:
    def test_explicit_new_init(self):
        l = l0 = list.__new__(list)
        l.__init__([1,2])
        assert l is l0
        assert l ==[1,2]
        list.__init__(l,[1,2,3])
        assert l is l0
        assert l ==[1,2,3]
        
    def test_extend_list(self):
        l = l0 = [1]
        l.extend([2])
        assert l is l0
        assert l == [1,2]

    def test_extend_tuple(self):
        l = l0 = [1]
        l.extend((2,))
        assert l is l0
        assert l == [1,2]

    def test_sort(self):
        l = l0 = [1, 5, 3, 0]
        l.sort()
        assert l is l0
        assert l == [0, 1, 3, 5]
        l = l0 = []
        l.sort()
        assert l is l0
        assert l == []
        l = l0 = [1]
        l.sort()
        assert l is l0
        assert l == [1]

    def test_sort_cmp(self):
        def lencmp(a,b): return cmp(len(a), len(b))
        l = [ 'a', 'fiver', 'tre', '' ]
        l.sort(lencmp)
        assert l == ['', 'a', 'tre', 'fiver']
        l = []
        l.sort(lencmp)
        assert l == []
        l = [ 'a' ]
        l.sort(lencmp)
        assert l == [ 'a' ]

    def test_sort_key(self):
        def lower(x): return x.lower()
        l = ['a', 'C', 'b']
        l.sort(key = lower)
        assert l == ['a', 'b', 'C']
        l = []
        l.sort(key = lower)
        assert l == []
        l = [ 'a' ]
        l.sort(key = lower)
        assert l == [ 'a' ]
        
    def test_sort_reversed(self):
        l = range(10)
        l.sort(reverse = True)
        assert l == range(9, -1, -1)
        l = []
        l.sort(reverse = True)
        assert l == []
        l = [1]
        l.sort(reverse = True)
        assert l == [1]

    def test_sort_cmp_key_reverse(self):
        def lower(x): return x.lower()
        l = ['a', 'C', 'b']
        l.sort(reverse = True, key = lower)
        assert l == ['C', 'b', 'a']
        
    def test_extended_slice(self):
        l = range(10)
        del l[::2]
        assert l ==[1,3,5,7,9]
        l[-2::-1] = l[:-1]
        assert l ==[7,5,3,1,9]
        del l[-1:2:-1]
        assert l ==[7,5,3]
        del l[:2]
        assert l ==[3]

    def test_delall(self):
        l = l0 = [1,2,3]
        del l[:]
        assert l is l0
        assert l == []

    def test_iadd(self):
        l = l0 = [1,2,3]
        l += [4,5]
        assert l is l0
        assert l == [1,2,3,4,5]

    def test_index(self):
        l = ['a', 'b', 'c', 'd', 'e', 'f']
        raises(TypeError, l.index, 'c', 0, 4.3)
        raises(TypeError, l.index, 'c', 1.0, 5.6)
