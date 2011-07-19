# coding: iso-8859-15
import random
from pypy.objspace.std.listobject import W_ListObject
from pypy.interpreter.error import OperationError

from pypy.conftest import gettestobjspace


class TestW_ListObject(object):

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

    def test_random_getitem(self):
        w = self.space.wrap
        s = list('qedx387tn3uixhvt 7fh387fymh3dh238 dwd-wq.dwq9')
        w_list = W_ListObject(self.space, map(w, s))
        keys = range(-len(s)-5, len(s)+5)
        choices = keys + [None]*12
        stepchoices = [None, None, None, 1, 1, -1, -1, 2, -2,
                       len(s)-1, len(s), len(s)+1,
                       -len(s)-1, -len(s), -len(s)+1]
        for i in range(40):
            keys.append(slice(random.choice(choices),
                              random.choice(choices),
                              random.choice(stepchoices)))
        random.shuffle(keys)
        for key in keys:
            try:
                expected = s[key]
            except IndexError:
                self.space.raises_w(self.space.w_IndexError,
                                    self.space.getitem, w_list, w(key))
            else:
                w_result = self.space.getitem(w_list, w(key))
                assert self.space.unwrap(w_result) == expected

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

    def test_random_setitem_delitem(self):
        w = self.space.wrap
        s = range(39)
        w_list = W_ListObject(self.space, map(w, s))
        expected = list(s)
        keys = range(-len(s)-5, len(s)+5)
        choices = keys + [None]*12
        stepchoices = [None, None, None, 1, 1, -1, -1, 2, -2,
                       len(s)-1, len(s), len(s)+1,
                       -len(s)-1, -len(s), -len(s)+1]
        for i in range(50):
            keys.append(slice(random.choice(choices),
                              random.choice(choices),
                              random.choice(stepchoices)))
        random.shuffle(keys)
        n = len(s)
        for key in keys:
            if random.random() < 0.15:
                random.shuffle(s)
                w_list = W_ListObject(self.space, map(w, s))
                expected = list(s)
            try:
                value = expected[key]
            except IndexError:
                self.space.raises_w(self.space.w_IndexError,
                                    self.space.setitem, w_list, w(key), w(42))
            else:
                if isinstance(value, int):   # non-slicing
                    if random.random() < 0.25:   # deleting
                        self.space.delitem(w_list, w(key))
                        del expected[key]
                    else:
                        self.space.setitem(w_list, w(key), w(n))
                        expected[key] = n
                        n += 1
                else:        # slice assignment
                    mode = random.choice(['samesize', 'resize', 'delete'])
                    if mode == 'delete':
                        self.space.delitem(w_list, w(key))
                        del expected[key]
                    elif mode == 'samesize':
                        newvalue = range(n, n+len(value))
                        self.space.setitem(w_list, w(key), w(newvalue))
                        expected[key] = newvalue
                        n += len(newvalue)
                    elif mode == 'resize' and key.step is None:
                        newvalue = range(n, n+random.randrange(0, 20))
                        self.space.setitem(w_list, w(key), w(newvalue))
                        expected[key] = newvalue
                        n += len(newvalue)
            assert self.space.unwrap(w_list) == expected

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


class AppTestW_ListObject(object):

    def test_getstrategyfromlist_w(self):
        l0 = ["a", "2", "a", True]

        # this raised TypeError on ListStrategies
        l1 = ["a", "2", True, "a"]
        l2 = [1, "2", "a", "a"]
        assert sorted(l1) == sorted(l2)

    def test_call_list(self):
        assert list('') == []
        assert list('abc') == ['a', 'b', 'c']
        assert list((1, 2)) == [1, 2]
        l = [1]
        assert list(l) is not l
        assert list(l) == l
        assert list(range(10)) == range(10)

    def test_explicit_new_init(self):
        l = l0 = list.__new__(list)
        l.__init__([1,2])
        assert l is l0
        assert l == [1,2]
        list.__init__(l, [1,2,3])
        assert l is l0
        assert l == [1,2,3]
        list.__init__(l, ['a', 'b', 'c'])
        assert l is l0
        assert l == ['a', 'b', 'c']

    def test_extend_list(self):
        l = l0 = [1]
        l.extend([2])
        assert l is l0
        assert l == [1,2]
        l = ['a']
        l.extend('b')
        assert l == ['a', 'b']
        l = ['a']
        l.extend([0])
        assert l == ['a', 0]
        l = range(10)
        l.extend([10])
        assert l == range(11)

        l = []
        m = [1,2,3]
        l.extend(m)
        m[0] = 5
        assert m == [5,2,3]
        assert l == [1,2,3]


    def test_extend_tuple(self):
        l = l0 = [1]
        l.extend((2,))
        assert l is l0
        assert l == [1,2]
        l = ['a']
        l.extend(('b',))
        assert l == ['a', 'b']

    def test_extend_iterable(self):
        l = l0 = [1]
        l.extend(iter([1, 2, 3, 4]))
        assert l is l0
        assert l == [1, 1, 2, 3, 4]
        l = l0 = ['a']
        l.extend(iter(['b', 'c', 'd']))
        assert l == ['a', 'b', 'c', 'd']
        assert l is l0

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

    def test_getitem(self):
        l = [1, 2, 3, 4, 5, 6, 9]
        assert l[0] == 1
        assert l[-1] == 9
        assert l[-2] == 6
        raises(IndexError, "l[len(l)]")
        raises(IndexError, "l[-len(l)-1]")
        l = ['a', 'b', 'c']
        assert l[0] == 'a'
        assert l[-1] == 'c'
        assert l[-2] == 'b'
        raises(IndexError, "l[len(l)]")

    def test_delitem(self):
        l = [1, 2, 3, 4, 5, 6, 9]
        del l[0]
        assert l == [2, 3, 4, 5, 6, 9]
        del l[-1]
        assert l == [2, 3, 4, 5, 6]
        del l[-2]
        assert l == [2, 3, 4, 6]
        raises(IndexError, "del l[len(l)]")
        raises(IndexError, "del l[-len(l)-1]")
        
        l = l0 = ['a', 'b', 'c']
        del l[0]
        assert l == ['b', 'c']
        del l[-1]
        assert l == ['b']
        del l[-1]
        assert l == []
        assert l is l0
        raises(IndexError, "del l[0]")

        l = range(10)
        del l[5]
        assert l == [0, 1, 2, 3, 4, 6, 7, 8, 9]

    def test_getitem_slice(self):
        l = range(10)
        assert l[::] == l
        del l[::2]
        assert l == [1,3,5,7,9]
        l[-2::-1] = l[:-1]
        assert l == [7,5,3,1,9]
        del l[-1:2:-1]
        assert l == [7,5,3]
        del l[:2]
        assert l == [3]
        assert l[1:] == []
        assert l[1::2] == []
        assert l[::] == l
        assert l[0::-2] == l
        assert l[-1::-5] == l
        
        l = ['']
        assert l[1:] == []
        assert l[1::2] == []
        assert l[::] == l
        assert l[0::-5] == l
        assert l[-1::-5] == l
        l.extend(['a', 'b'])
        assert l[::-1] == ['b', 'a', '']

        l = [1,2,3,4,5]
        assert l[1:0:None] == []
        assert l[1:0] == []

    def test_delall(self):
        l = l0 = [1,2,3]
        del l[:]
        assert l is l0
        assert l == []
        l = ['a', 'b']
        del l[:]
        assert l == []
        l = range(5)
        del l[:]
        assert l == []

    def test_iadd(self):
        l = l0 = [1,2,3]
        l += [4,5]
        assert l is l0
        assert l == [1,2,3,4,5]

        l = l0 = ['a', 'b', 'c']
        l1 = l[:]
        l += ['d']
        assert l is l0
        assert l == ['a', 'b', 'c', 'd']
        l1 += [0]
        assert l1 == ['a', 'b', 'c', 0]

    def test_iadd_iterable(self):
        l = l0 = [1,2,3]
        l += iter([4,5])
        assert l is l0
        assert l == [1,2,3,4,5]

    def test_iadd_subclass(self):
        class Bar(object):
            def __radd__(self, other):
                return ('radd', self, other)
        bar = Bar()
        l1 = [1,2,3]
        l1 += bar
        assert l1 == ('radd', bar, [1,2,3])

    def test_add_lists(self):
        l1 = [1,2,3]
        l2 = [4,5,6]
        l3 = l1 + l2
        assert l3 == [1,2,3,4,5,6]

        l4 = range(3)
        l5 = l4 + l2
        assert l5 == [0,1,2,4,5,6]

    def test_imul(self):
        l = l0 = [4,3]
        l *= 2
        assert l is l0
        assert l == [4,3,4,3]
        l *= 0
        assert l is l0
        assert l == []
        l = l0 = [4,3]
        l *= (-1)
        assert l is l0
        assert l == []
        
        l = l0 = ['a', 'b']
        l *= 2
        assert l is l0
        assert l == ['a', 'b', 'a', 'b']
        l *= 0
        assert l is l0
        assert l == []
        l = ['a']
        l *= -5
        assert l == []

        l = range(2)
        l *= 2
        assert l == [0, 1, 0, 1]

    def test_mul_errors(self):
        try:
            [1, 2, 3] * (3,)
        except TypeError:
            pass

    def test_index(self):
        c = range(10)
        assert c.index(0) == 0
        raises(ValueError, c.index, 10)
        
        c = list('hello world')
        assert c.index('l') == 2
        raises(ValueError, c.index, '!')
        assert c.index('l', 3) == 3
        assert c.index('l', 4) == 9
        raises(ValueError, c.index, 'l', 10)
        assert c.index('l', -5) == 9
        assert c.index('l', -25) == 2
        assert c.index('o', 1, 5) == 4
        raises(ValueError, c.index, 'o', 1, 4)
        assert c.index('o', 1, 5-11) == 4
        raises(ValueError, c.index, 'o', 1, 4-11)
        raises(TypeError, c.index, 'c', 0, 4.3)
        raises(TypeError, c.index, 'c', 1.0, 5.6)

        c = [0, 2, 4]
        assert c.index(0) == 0
        raises(ValueError, c.index, 3)

    def test_ass_slice(self):
        l = range(6)
        l[1:3] = 'abc'
        assert l == [0, 'a', 'b', 'c', 3, 4, 5]
        l = []
        l[:-3] = []
        assert l == []
        l = range(6)
        l[:] = []
        assert l == []

        l = l0 = ['a', 'b']
        l[1:1] = ['ae']
        assert l == ['a', 'ae', 'b']
        l[1:100] = ['B']
        assert l == ['a', 'B']
        l[:] = []
        assert l == []
        assert l is l0

    def test_ass_extended_slice(self):
        l = l0 = ['a', 'b', 'c']
        l[::-1] = ['a', 'b', 'c']
        assert l == ['c', 'b', 'a']
        l[::-2] = [0, 1]
        assert l == [1, 'b', 0]
        l[-1:5:2] = [2]
        assert l == [1, 'b', 2]
        l[:-1:2] = [0]
        assert l == [0, 'b', 2]
        assert l is l0

        l = [1,2,3]
        raises(ValueError, "l[0:2:2] = [1,2,3,4]")
        raises(ValueError, "l[::2] = []")

    def test_recursive_repr(self):
        l = []
        assert repr(l) == '[]'
        l.append(l)
        assert repr(l) == '[[...]]'

    def test_append(self):
        l = []
        l.append('X')
        assert l == ['X']
        l.append('Y')
        l.append('Z')
        assert l == ['X', 'Y', 'Z']

        l = []
        l.append(0)
        assert l == [0]
        for x in range(1, 5):
            l.append(x)
        assert l == range(5)

        l = range(4)
        l.append(4)
        assert l == range(5)

    def test_count(self):
        c = list('hello')
        assert c.count('l') == 2
        assert c.count('h') == 1
        assert c.count('w') == 0

    def test_insert(self):
        c = list('hello world')
        c.insert(0, 'X')
        assert c[:4] == ['X', 'h', 'e', 'l']
        c.insert(2, 'Y')
        c.insert(-2, 'Z')
        assert ''.join(c) == 'XhYello worZld'

        ls = [1, 2, 3, 4, 5, 6, 7]
        for i in range(5):
            ls.insert(0, i)
        assert len(ls) == 12

    def test_pop(self):
        c = list('hello world')
        s = ''
        for i in range(11):
            s += c.pop()
        assert s == 'dlrow olleh'
        raises(IndexError, c.pop)
        assert len(c) == 0

        l = range(10)
        l.pop()
        assert l == range(9)

    def test_remove(self):
        c = list('hello world')
        c.remove('l')
        assert ''.join(c) == 'helo world'
        c.remove('l')
        assert ''.join(c) == 'heo world'
        c.remove('l')
        assert ''.join(c) == 'heo word'
        raises(ValueError, c.remove, 'l')
        assert ''.join(c) == 'heo word'

        l = range(5)
        l.remove(2)
        assert l == [0, 1, 3, 4]
        l = [0, 3, 5]
        raises(ValueError, c.remove, 2)

    def test_reverse(self):
        c = list('hello world')
        c.reverse()
        assert ''.join(c) == 'dlrow olleh'

    def test_reversed(self):
        assert list(list('hello').__reversed__()) == ['o', 'l', 'l', 'e', 'h']
        assert list(reversed(list('hello'))) == ['o', 'l', 'l', 'e', 'h']

    def test_mutate_while_remove(self):
        class Mean(object):
            def __init__(self, i):
                self.i = i
            def __eq__(self, other):
                if self.i == 9:
                    del l[i - 1]
                    return True
                else:
                    return False
        l = [Mean(i) for i in range(10)]
        # does not crash
        l.remove(None)
        class Mean2(object):
            def __init__(self, i):
                self.i = i
            def __eq__(self, other):
                l.append(self.i)
                return False
        l = [Mean2(i) for i in range(10)]
        # does not crash
        l.remove(5)
        assert l[10:] == [0, 1, 2, 3, 4, 6, 7, 8, 9]

    def test_mutate_while_extend(self):
        # this used to segfault pypy-c (with py.test -A)
        import sys
        if hasattr(sys, 'pypy_translation_info'):
            if sys.pypy_translation_info['translation.gc'] == 'boehm':
                skip("not reliable on top of Boehm")
        class A(object):
            def __del__(self):
                print 'del'
                del lst[:]
        for i in range(10):
            keepalive = []
            lst = list(str(i)) * 100
            A()
            while lst:
                keepalive.append(lst[:])

    def test___getslice__(self):
        l = [1,2,3,4]
        res = l.__getslice__(0, 2)
        assert res == [1, 2]

    def test___setslice__(self):
        l = [1,2,3,4]
        l.__setslice__(0, 2, [5, 6])
        assert l == [5, 6, 3, 4]

    def test___delslice__(self):
        l = [1,2,3,4]
        l.__delslice__(0, 2)
        assert l == [3, 4]

    def test_unicode(self):
        s = u"äöü"
        assert s.encode("ascii", "replace") == "???"
        assert s.encode("ascii", "ignore") == ""

        l1 = [s.encode("ascii", "replace")]
        assert l1[0] == "???"

        l2 = [s.encode("ascii", "ignore")]
        assert l2[0] == ""

        l3 = [s]
        assert l1[0].encode("ascii", "replace") == "???"

class AppTestForRangeLists(AppTestW_ListObject):

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withrangelist" :
                                       True})

    def test_range_simple_backwards(self):
        x = range(5,1)
        assert x == []

    def test_range_big_start(self):
        x = range(1,10)
        x[22:0:-1] == range(1,10)

    def test_range_list_invalid_slice(self):
        x = [1,2,3,4]
        assert x[10:0] == []
        assert x[10:0:None] == []

        x = range(1,5)
        assert x[10:0] == []
        assert x[10:0:None] == []

        assert x[0:22] == [1,2,3,4]
        assert x[-1:10] == [4]

        assert x[0:22:None] == [1,2,3,4]
        assert x[-1:10:None] == [4]

    def test_range_backwards(self):
        x = range(1,10)
        assert x[22:-10] == []
        assert x[22:-10:-1] == [9,8,7,6,5,4,3,2,1]
        assert x[10:3:-1] == [9,8,7,6,5]
        assert x[10:3:-2] == [9,7,5]
        assert x[1:5:-1] == []

class AppTestListFastSubscr:

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.optimized_list_getitem" :
                                       True})

    def test_getitem(self):
        import operator
        l = [0, 1, 2, 3, 4]
        for i in xrange(5):
            assert l[i] == i
        assert l[3:] == [3, 4]
        raises(TypeError, operator.getitem, l, "str")
