#from __future__ import nested_scopes
from pypy.objspace.std.tupleobject import W_TupleObject
from pypy.interpreter.error import OperationError

class TestW_TupleObject:

    def test_is_true(self):
        w = self.space.wrap
        w_tuple = W_TupleObject([])
        assert self.space.is_true(w_tuple) == False
        w_tuple = W_TupleObject([w(5)])
        assert self.space.is_true(w_tuple) == True
        w_tuple = W_TupleObject([w(5), w(3)])
        assert self.space.is_true(w_tuple) == True

    def test_len(self):
        w = self.space.wrap
        w_tuple = W_TupleObject([])
        assert self.space.eq_w(self.space.len(w_tuple), w(0))
        w_tuple = W_TupleObject([w(5)])
        assert self.space.eq_w(self.space.len(w_tuple), w(1))
        w_tuple = W_TupleObject([w(5), w(3), w(99)]*111)
        assert self.space.eq_w(self.space.len(w_tuple), w(333))

    def test_getitem(self):
        w = self.space.wrap
        w_tuple = W_TupleObject([w(5), w(3)])
        assert self.space.eq_w(self.space.getitem(w_tuple, w(0)), w(5))
        assert self.space.eq_w(self.space.getitem(w_tuple, w(1)), w(3))
        assert self.space.eq_w(self.space.getitem(w_tuple, w(-2)), w(5))
        assert self.space.eq_w(self.space.getitem(w_tuple, w(-1)), w(3))
        self.space.raises_w(self.space.w_IndexError,
                            self.space.getitem, w_tuple, w(2))
        self.space.raises_w(self.space.w_IndexError,
                            self.space.getitem, w_tuple, w(42))
        self.space.raises_w(self.space.w_IndexError,
                            self.space.getitem, w_tuple, w(-3))

    def test_iter(self):
        w = self.space.wrap
        w_tuple = W_TupleObject([w(5), w(3), w(99)])
        w_iter = self.space.iter(w_tuple)
        assert self.space.eq_w(self.space.next(w_iter), w(5))
        assert self.space.eq_w(self.space.next(w_iter), w(3))
        assert self.space.eq_w(self.space.next(w_iter), w(99))
        raises(OperationError, self.space.next, w_iter)
        raises(OperationError, self.space.next, w_iter)

    def test_contains(self):
        w = self.space.wrap
        w_tuple = W_TupleObject([w(5), w(3), w(99)])
        assert self.space.eq_w(self.space.contains(w_tuple, w(5)),
                           self.space.w_True)
        assert self.space.eq_w(self.space.contains(w_tuple, w(99)),
                           self.space.w_True)
        assert self.space.eq_w(self.space.contains(w_tuple, w(11)),
                           self.space.w_False)
        assert self.space.eq_w(self.space.contains(w_tuple, w_tuple),
                           self.space.w_False)

    def test_add(self):
        w = self.space.wrap
        w_tuple0 = W_TupleObject([])
        w_tuple1 = W_TupleObject([w(5), w(3), w(99)])
        w_tuple2 = W_TupleObject([w(-7)] * 111)
        assert self.space.eq_w(self.space.add(w_tuple1, w_tuple1),
                           W_TupleObject([w(5), w(3), w(99),
                                                      w(5), w(3), w(99)]))
        assert self.space.eq_w(self.space.add(w_tuple1, w_tuple2),
                           W_TupleObject([w(5), w(3), w(99)] + [w(-7)] * 111))
        assert self.space.eq_w(self.space.add(w_tuple1, w_tuple0), w_tuple1)
        assert self.space.eq_w(self.space.add(w_tuple0, w_tuple2), w_tuple2)

    def test_mul(self):
        # only testing right mul at the moment
        w = self.space.wrap
        arg = w(2)
        n = 3
        w_tup = W_TupleObject([arg])
        w_tup3 = W_TupleObject([arg]*n)
        w_res = self.space.mul(w_tup, w(n))
        assert self.space.eq_w(w_tup3, w_res)
        # commute
        w_res = self.space.mul(w(n), w_tup)
        assert self.space.eq_w(w_tup3, w_res)
        # check tuple*1 is identity (optimisation tested by CPython tests)
        w_res = self.space.mul(w_tup, w(1))
        assert w_res is w_tup

    def test_getslice(self):
        w = self.space.wrap

        def test1(testtuple, start, stop, step, expected):
            w_slice  = self.space.newslice(w(start), w(stop), w(step))
            w_tuple = W_TupleObject([w(i) for i in testtuple])
            w_result = self.space.getitem(w_tuple, w_slice)
            assert self.space.unwrap(w_result) == expected
        
        for testtuple in [(), (5,3,99), tuple(range(5,555,10))]:
            for start in [-2, -1, 0, 1, 10]:
                for end in [-1, 0, 2, 999]:
                    test1(testtuple, start, end, 1, testtuple[start:end])

        test1((5,7,1,4), 3, 1, -2,  (4,))
        test1((5,7,1,4), 3, 0, -2,  (4, 7))
        test1((5,7,1,4), 3, -1, -2, ())
        test1((5,7,1,4), -2, 11, 2, (1,))
        test1((5,7,1,4), -3, 11, 2, (7, 4))
        test1((5,7,1,4), -5, 11, 2, (5, 1))

    def test_eq(self):
        w = self.space.wrap
        
        w_tuple0 = W_TupleObject([])
        w_tuple1 = W_TupleObject([w(5), w(3), w(99)])
        w_tuple2 = W_TupleObject([w(5), w(3), w(99)])
        w_tuple3 = W_TupleObject([w(5), w(3), w(99), w(-1)])

        assert self.space.eq_w(self.space.eq(w_tuple0, w_tuple1),
                           self.space.w_False)
        assert self.space.eq_w(self.space.eq(w_tuple1, w_tuple0),
                           self.space.w_False)
        assert self.space.eq_w(self.space.eq(w_tuple1, w_tuple1),
                           self.space.w_True)
        assert self.space.eq_w(self.space.eq(w_tuple1, w_tuple2),
                           self.space.w_True)
        assert self.space.eq_w(self.space.eq(w_tuple2, w_tuple3),
                           self.space.w_False)
    def test_ne(self):
        w = self.space.wrap
        
        w_tuple0 = W_TupleObject([])
        w_tuple1 = W_TupleObject([w(5), w(3), w(99)])
        w_tuple2 = W_TupleObject([w(5), w(3), w(99)])
        w_tuple3 = W_TupleObject([w(5), w(3), w(99), w(-1)])

        assert self.space.eq_w(self.space.ne(w_tuple0, w_tuple1),
                           self.space.w_True)
        assert self.space.eq_w(self.space.ne(w_tuple1, w_tuple0),
                           self.space.w_True)
        assert self.space.eq_w(self.space.ne(w_tuple1, w_tuple1),
                           self.space.w_False)
        assert self.space.eq_w(self.space.ne(w_tuple1, w_tuple2),
                           self.space.w_False)
        assert self.space.eq_w(self.space.ne(w_tuple2, w_tuple3),
                           self.space.w_True)
    def test_lt(self):
        w = self.space.wrap
        
        w_tuple0 = W_TupleObject([])
        w_tuple1 = W_TupleObject([w(5), w(3), w(99)])
        w_tuple2 = W_TupleObject([w(5), w(3), w(99)])
        w_tuple3 = W_TupleObject([w(5), w(3), w(99), w(-1)])
        w_tuple4 = W_TupleObject([w(5), w(3), w(9), w(-1)])

        assert self.space.eq_w(self.space.lt(w_tuple0, w_tuple1),
                           self.space.w_True)
        assert self.space.eq_w(self.space.lt(w_tuple1, w_tuple0),
                           self.space.w_False)
        assert self.space.eq_w(self.space.lt(w_tuple1, w_tuple1),
                           self.space.w_False)
        assert self.space.eq_w(self.space.lt(w_tuple1, w_tuple2),
                           self.space.w_False)
        assert self.space.eq_w(self.space.lt(w_tuple2, w_tuple3),
                           self.space.w_True)
        assert self.space.eq_w(self.space.lt(w_tuple4, w_tuple3),
                           self.space.w_True)
        
    def test_ge(self):
        w = self.space.wrap
        
        w_tuple0 = W_TupleObject([])
        w_tuple1 = W_TupleObject([w(5), w(3), w(99)])
        w_tuple2 = W_TupleObject([w(5), w(3), w(99)])
        w_tuple3 = W_TupleObject([w(5), w(3), w(99), w(-1)])
        w_tuple4 = W_TupleObject([w(5), w(3), w(9), w(-1)])

        assert self.space.eq_w(self.space.ge(w_tuple0, w_tuple1),
                           self.space.w_False)
        assert self.space.eq_w(self.space.ge(w_tuple1, w_tuple0),
                           self.space.w_True)
        assert self.space.eq_w(self.space.ge(w_tuple1, w_tuple1),
                           self.space.w_True)
        assert self.space.eq_w(self.space.ge(w_tuple1, w_tuple2),
                           self.space.w_True)
        assert self.space.eq_w(self.space.ge(w_tuple2, w_tuple3),
                           self.space.w_False)
        assert self.space.eq_w(self.space.ge(w_tuple4, w_tuple3),
                           self.space.w_False)
        
    def test_gt(self):
        w = self.space.wrap
        
        w_tuple0 = W_TupleObject([])
        w_tuple1 = W_TupleObject([w(5), w(3), w(99)])
        w_tuple2 = W_TupleObject([w(5), w(3), w(99)])
        w_tuple3 = W_TupleObject([w(5), w(3), w(99), w(-1)])
        w_tuple4 = W_TupleObject([w(5), w(3), w(9), w(-1)])

        assert self.space.eq_w(self.space.gt(w_tuple0, w_tuple1),
                           self.space.w_False)
        assert self.space.eq_w(self.space.gt(w_tuple1, w_tuple0),
                           self.space.w_True)
        assert self.space.eq_w(self.space.gt(w_tuple1, w_tuple1),
                           self.space.w_False)
        assert self.space.eq_w(self.space.gt(w_tuple1, w_tuple2),
                           self.space.w_False)
        assert self.space.eq_w(self.space.gt(w_tuple2, w_tuple3),
                           self.space.w_False)
        assert self.space.eq_w(self.space.gt(w_tuple4, w_tuple3),
                           self.space.w_False)
        
    def test_le(self):
        w = self.space.wrap
        
        w_tuple0 = W_TupleObject([])
        w_tuple1 = W_TupleObject([w(5), w(3), w(99)])
        w_tuple2 = W_TupleObject([w(5), w(3), w(99)])
        w_tuple3 = W_TupleObject([w(5), w(3), w(99), w(-1)])
        w_tuple4 = W_TupleObject([w(5), w(3), w(9), w(-1)])

        assert self.space.eq_w(self.space.le(w_tuple0, w_tuple1),
                           self.space.w_True)
        assert self.space.eq_w(self.space.le(w_tuple1, w_tuple0),
                           self.space.w_False)
        assert self.space.eq_w(self.space.le(w_tuple1, w_tuple1),
                           self.space.w_True)
        assert self.space.eq_w(self.space.le(w_tuple1, w_tuple2),
                           self.space.w_True)
        assert self.space.eq_w(self.space.le(w_tuple2, w_tuple3),
                           self.space.w_True)
        assert self.space.eq_w(self.space.le(w_tuple4, w_tuple3),
                           self.space.w_True)


class AppTestW_TupleObject:

    def test_is_true(self):
        assert not ()
        assert (5,)
        assert (5,3)

    def test_len(self):
        assert len(()) == 0
        assert len((5,)) == 1
        assert len((5,3,99,1,2,3,4,5,6)) == 9 

    def test_getitem(self):
        assert (5,3)[0] == 5
        assert (5,3)[1] == 3
        assert (5,3)[-1] == 3
        assert (5,3)[-2] == 5
        raises(IndexError, "(5,3)[2]")
        raises(IndexError, "(5,)[1]")
        raises(IndexError, "()[0]")

    def test_iter(self):
        t = (5,3,99)
        i = iter(t)
        assert i.next() == 5
        assert i.next() == 3
        assert i.next() == 99
        raises(StopIteration, i.next)

    def test_contains(self):
        t = (5,3,99)
        assert 5 in t
        assert 99 in t
        assert not 11 in t
        assert not t in t

    def test_add(self):
        t0 = ()
        t1 = (5,3,99)
        assert t0 + t0 == t0
        assert t1 + t0 == t1
        assert t1 + t1 == (5,3,99,5,3,99)

    def test_mul(self):
        assert () * 10 == ()
        assert (5,) * 3 == (5,5,5)
        assert (5,2) * 2 == (5,2,5,2)
        t = (1,2,3)
        assert (t * 1) is t

    def test_mul_subtype(self):
        class T(tuple): pass
        t = T([1,2,3])
        assert (t * 1) is not t
        assert (t * 1) == t

    def test_getslice_2(self):
        assert (5,2,3)[1:2] == (2,)

    def test_eq(self):
        t0 = ()
        t1 = (5,3,99)
        t2 = (5,3,99)
        t3 = (5,3,99,-1)
        t4 = (5,3,9,1)
        assert not t0 == t1
        assert t0 != t1
        assert t1 == t2
        assert t2 == t1
        assert t3 != t2
        assert not t3 == t2
        assert not t2 == t3
        assert t3 > t4
        assert t2 > t4
        assert t3 > t2
        assert t1 > t0
        assert t0 <= t0
        assert not t0 < t0
        assert t4 >= t0
        assert t3 >= t2
        assert t2 <= t3

    def test_hash(self):
        # check that hash behaves as in 2.4 for at least 31 bits
        assert hash(()) & 0x7fffffff == 0x35d373
        assert hash((12,)) & 0x7fffffff == 0x1cca0557
        assert hash((12,34)) & 0x7fffffff == 0x153e2a41

    def test_getnewargs(self):
        assert  () .__getnewargs__() == ((),)

    def test_repr(self):
        assert repr((1,)) == '(1,)'
        assert repr(()) == '()'
        assert repr((1,2,3)) == '(1, 2, 3)'

    def test_getslice(self):
        assert ('a', 'b', 'c').__getslice__(-17, 2) == ('a', 'b')

    def test_count(self):
        assert ().count(4) == 0
        assert (1, 2, 3, 4).count(3) == 1
        assert (1, 2, 3, 4).count(5) == 0
        assert (1, 1, 1).count(1) == 3

    def test_index(self):
        raises(ValueError, ().index, 4)
        (1, 2).index(1) == 0
        (3, 4, 5).index(4) == 1
        raises(ValueError, (1, 2, 3, 4).index, 5)
        assert (4, 2, 3, 4).index(4, 1) == 3
        assert (4, 4, 4).index(4, 1, 2) == 1
        raises(ValueError, (1, 2, 3, 4).index, 4, 0, 2)
