#from __future__ import nested_scopes
import autopath
from pypy.objspace.std.tupleobject import W_TupleObject
from pypy.interpreter.error import OperationError


objspacename = 'std'

class TestW_TupleObject:

    def test_is_true(self):
        w = self.space.wrap
        w_tuple = W_TupleObject(self.space, [])
        assert self.space.is_true(w_tuple) == False
        w_tuple = W_TupleObject(self.space, [w(5)])
        assert self.space.is_true(w_tuple) == True
        w_tuple = W_TupleObject(self.space, [w(5), w(3)])
        assert self.space.is_true(w_tuple) == True

    def test_len(self):
        w = self.space.wrap
        w_tuple = W_TupleObject(self.space, [])
        assert self.space.eq_w(self.space.len(w_tuple), w(0))
        w_tuple = W_TupleObject(self.space, [w(5)])
        assert self.space.eq_w(self.space.len(w_tuple), w(1))
        w_tuple = W_TupleObject(self.space, [w(5), w(3), w(99)]*111)
        assert self.space.eq_w(self.space.len(w_tuple), w(333))

    def test_getitem(self):
        w = self.space.wrap
        w_tuple = W_TupleObject(self.space, [w(5), w(3)])
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
        w_tuple = W_TupleObject(self.space, [w(5), w(3), w(99)])
        w_iter = self.space.iter(w_tuple)
        assert self.space.eq_w(self.space.next(w_iter), w(5))
        assert self.space.eq_w(self.space.next(w_iter), w(3))
        assert self.space.eq_w(self.space.next(w_iter), w(99))
        raises(OperationError, self.space.next, w_iter)
        raises(OperationError, self.space.next, w_iter)

    def test_contains(self):
        w = self.space.wrap
        w_tuple = W_TupleObject(self.space, [w(5), w(3), w(99)])
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
        w_tuple0 = W_TupleObject(self.space, [])
        w_tuple1 = W_TupleObject(self.space, [w(5), w(3), w(99)])
        w_tuple2 = W_TupleObject(self.space, [w(-7)] * 111)
        assert self.space.eq_w(self.space.add(w_tuple1, w_tuple1),
                           W_TupleObject(self.space, [w(5), w(3), w(99),
                                                      w(5), w(3), w(99)]))
        assert self.space.eq_w(self.space.add(w_tuple1, w_tuple2),
                           W_TupleObject(self.space,
                                         [w(5), w(3), w(99)] + [w(-7)] * 111))
        assert self.space.eq_w(self.space.add(w_tuple1, w_tuple0), w_tuple1)
        assert self.space.eq_w(self.space.add(w_tuple0, w_tuple2), w_tuple2)

    def test_mul(self):
        # only testing right mul at the moment
        w = self.space.wrap
        arg = w(2)
        n = 3
        w_tup = W_TupleObject(self.space, [arg])
        w_tup3 = W_TupleObject(self.space, [arg]*n)
        w_res = self.space.mul(w_tup, w(n))
        assert self.space.eq_w(w_tup3, w_res)
        # commute
        w_res = self.space.mul(w(n), w_tup)
        assert self.space.eq_w(w_tup3, w_res)

    def test_getslice(self):
        w = self.space.wrap

        def test1(testtuple, start, stop, step, expected):
            w_slice  = self.space.newslice(w(start), w(stop), w(step))
            w_tuple = W_TupleObject(self.space, [w(i) for i in testtuple])
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
        
        w_tuple0 = W_TupleObject(self.space, [])
        w_tuple1 = W_TupleObject(self.space, [w(5), w(3), w(99)])
        w_tuple2 = W_TupleObject(self.space, [w(5), w(3), w(99)])
        w_tuple3 = W_TupleObject(self.space, [w(5), w(3), w(99), w(-1)])

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
        
        w_tuple0 = W_TupleObject(self.space, [])
        w_tuple1 = W_TupleObject(self.space, [w(5), w(3), w(99)])
        w_tuple2 = W_TupleObject(self.space, [w(5), w(3), w(99)])
        w_tuple3 = W_TupleObject(self.space, [w(5), w(3), w(99), w(-1)])

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
        
        w_tuple0 = W_TupleObject(self.space, [])
        w_tuple1 = W_TupleObject(self.space, [w(5), w(3), w(99)])
        w_tuple2 = W_TupleObject(self.space, [w(5), w(3), w(99)])
        w_tuple3 = W_TupleObject(self.space, [w(5), w(3), w(99), w(-1)])
        w_tuple4 = W_TupleObject(self.space, [w(5), w(3), w(9), w(-1)])

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
        
        w_tuple0 = W_TupleObject(self.space, [])
        w_tuple1 = W_TupleObject(self.space, [w(5), w(3), w(99)])
        w_tuple2 = W_TupleObject(self.space, [w(5), w(3), w(99)])
        w_tuple3 = W_TupleObject(self.space, [w(5), w(3), w(99), w(-1)])
        w_tuple4 = W_TupleObject(self.space, [w(5), w(3), w(9), w(-1)])

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
        
        w_tuple0 = W_TupleObject(self.space, [])
        w_tuple1 = W_TupleObject(self.space, [w(5), w(3), w(99)])
        w_tuple2 = W_TupleObject(self.space, [w(5), w(3), w(99)])
        w_tuple3 = W_TupleObject(self.space, [w(5), w(3), w(99), w(-1)])
        w_tuple4 = W_TupleObject(self.space, [w(5), w(3), w(9), w(-1)])

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
        
        w_tuple0 = W_TupleObject(self.space, [])
        w_tuple1 = W_TupleObject(self.space, [w(5), w(3), w(99)])
        w_tuple2 = W_TupleObject(self.space, [w(5), w(3), w(99)])
        w_tuple3 = W_TupleObject(self.space, [w(5), w(3), w(99), w(-1)])
        w_tuple4 = W_TupleObject(self.space, [w(5), w(3), w(9), w(-1)])

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
