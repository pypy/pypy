import autopath


class AppTestMap:

   def test_trivial_map_one_seq(self):
      assert map(lambda x: x+2, [1, 2, 3, 4]) == [3, 4, 5, 6]

   def test_trivial_map_two_seq(self):
      assert map(lambda x,y: x+y,
                           [1, 2, 3, 4],[1, 2, 3, 4]) == (
                       [2, 4, 6, 8])

   def test_trivial_map_sizes_dont_match_and_should(self):
      raises(TypeError, map, lambda x,y: x+y, [1, 2, 3, 4], [1, 2, 3])

   def test_trivial_map_no_arguments(self):
      raises(TypeError, map)

   def test_trivial_map_no_function_no_seq(self):
      raises(TypeError, map, None)

   def test_trivial_map_no_fuction_one_seq(self):
      assert map(None, [1, 2, 3]) == [1, 2, 3]

   def test_trivial_map_no_function(self):
      assert map(None, [1,2,3], [4,5,6], [7,8], [1]) == (
                       [(1, 4, 7, 1), (2, 5, 8, None), (3, 6, None, None)])

   def test_map_identity1(self):
      a = ['1', 2, 3, 'b', None]
      b = a[:]
      assert map(lambda x: x, a) == a
      assert a == b

   def test_map_None(self):
      a = ['1', 2, 3, 'b', None]
      b = a[:]
      assert map(None, a) == a
      assert a == b

   def test_map_badoperation(self):
      a = ['1', 2, 3, 'b', None]
      raises(TypeError, map, lambda x: x+1, a)

   def test_map_multiply_identity(self):
      a = ['1', 2, 3, 'b', None]
      b = [ 2, 3, 4, 5, 6]
      assert map(None, a, b) == [('1', 2), (2, 3), (3, 4), ('b', 5), (None, 6)]

   def test_map_multiply(self):
      a = [1, 2, 3, 4]
      b = [0, 1, 1, 1]
      assert map(lambda x, y: x+y, a, b) == [1, 2, 4, 5]

   def test_map_multiply(self):
      a = [1, 2, 3, 4, 5]
      b = []
      assert map(lambda x, y: x, a, b) == a

class AppTestZip:
   def test_one_list(self):
      assert zip([1,2,3]) == [(1,), (2,), (3,)]

   def test_three_lists(self):
      assert zip([1,2,3], [1,2], [1,2,3]) == [(1,1,1), (2,2,2)]

class AppTestReduce:
   def test_None(self):
       raises(TypeError, reduce, lambda x, y: x+y, [1,2,3], None)

   def test_sum(self):
       assert reduce(lambda x, y: x+y, [1,2,3,4], 0) == 10
       assert reduce(lambda x, y: x+y, [1,2,3,4]) == 10

   def test_minus(self):
       assert reduce(lambda x, y: x-y, [10, 2, 8]) == 0
       assert reduce(lambda x, y: x-y, [2, 8], 10) == 0

class AppTestFilter:
   def test_None(self):
       assert filter(None, ['a', 'b', 1, 0, None]) == ['a', 'b', 1]

   def test_return_type(self):
       txt = "This is a test text"
       assert filter(None, txt) == txt
       tup = ("a", None, 0, [], 1)
       assert filter(None, tup) == ("a", 1)

   def test_function(self):
       assert filter(lambda x: x != "a", "a small text") == " smll text"
       assert filter(lambda x: x < 20, [3, 33, 5, 55]) == [3, 5]

   def test_filter_tuple_calls_getitem(self):
       class T(tuple):
           def __getitem__(self, i):
               return i * 10
       assert filter(lambda x: x != 20, T("abcd")) == (0, 10, 30)

class AppTestXRange:
   def test_xrange(self):
      x = xrange(2, 9, 3)
      assert x[1] == 5
      assert len(x) == 3
      assert list(x) == [2, 5, 8]
      # test again, to make sure that xrange() is not its own iterator
      assert list(x) == [2, 5, 8]

   def test_xrange_iter(self):
      x = xrange(2, 9, 3)
      it = iter(x)
      assert iter(it) is it
      assert len(it) == 3
      assert it.next() == 2
      assert len(it) == 2
      assert it.next() == 5
      assert len(it) == 1
      assert it.next() == 8
      assert len(it) == 0
      raises(StopIteration, it.next)
      assert len(it) == 0
      # test again, to make sure that xrange() is not its own iterator
      assert iter(x).next() == 2

class AppTestReversed:
   def test_reversed(self):
      r = reversed("hello")
      assert iter(r) is r
      assert len(r) == 5
      assert r.next() == "o"
      assert r.next() == "l"
      assert r.next() == "l"
      assert r.next() == "e"
      assert len(r) == 1
      assert r.next() == "h"
      assert len(r) == 0
      raises(StopIteration, r.next)
      assert len(r) == 0
      assert list(reversed(list(reversed("hello")))) == ['h','e','l','l','o']
      raises(TypeError, reversed, reversed("hello"))

class AppTestApply:
   def test_apply(self):
      def f(*args, **kw):
         return args, kw
      args = (1,3)
      kw = {'a': 1, 'b': 4}
      assert apply(f) == ((), {})
      assert apply(f, args) == (args, {})
      assert apply(f, args, kw) == (args, kw)

class AppTestAllAny:
    """
    These are copied directly and replicated from the Python 2.5 source code.
    """

    def test_all(self):

        class TestFailingBool(object):
            def __nonzero__(self):
                raise RuntimeError
        class TestFailingIter(object):
            def __iter__(self):
                raise RuntimeError

        assert all([2, 4, 6]) == True
        assert all([2, None, 6]) == False
        raises(RuntimeError, all, [2, TestFailingBool(), 6])
        raises(RuntimeError, all, TestFailingIter())
        raises(TypeError, all, 10)               # Non-iterable
        raises(TypeError, all)                   # No args
        raises(TypeError, all, [2, 4, 6], [])    # Too many args
        assert all([]) == True                   # Empty iterator
        S = [50, 60]
        assert all([x > 42 for x in S]) == True
        S = [50, 40, 60]
        assert all([x > 42 for x in S]) == False

    def test_any(self):

        class TestFailingBool(object):
            def __nonzero__(self):
                raise RuntimeError
        class TestFailingIter(object):
            def __iter__(self):
                raise RuntimeError

        assert any([None, None, None]) == False
        assert any([None, 4, None]) == True
        raises(RuntimeError, any, [None, TestFailingBool(), 6])
        raises(RuntimeError, all, TestFailingIter())
        raises(TypeError, any, 10)               # Non-iterable
        raises(TypeError, any)                   # No args
        raises(TypeError, any, [2, 4, 6], [])    # Too many args
        assert any([]) == False                  # Empty iterator
        S = [40, 60, 30]
        assert any([x > 42 for x in S]) == True
        S = [10, 20, 30]
        assert any([x > 42 for x in S]) == False

