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
