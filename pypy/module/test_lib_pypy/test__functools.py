from _functools import reduce

class TestRange:

   def test_range_toofew(self):
      raises(TypeError, range)

   def test_range_toomany(self):
      raises(TypeError, range,  1, 2, 3, 4)

   def test_range_one(self):
      assert list(range(1)) == [0]

   def test_range_posstartisstop(self):
      assert list(range(1, 1)) == []

   def test_range_negstartisstop(self):
      assert list(range(-1, -1)) == []

   def test_range_zero(self):
      assert list(range(0)) == []

   def test_range_twoargs(self):
      assert list(range(1, 2)) == [1]

   def test_range_decreasingtwoargs(self):
      assert list(range(3, 1)) == []

   def test_range_negatives(self):
      assert list(range(-3)) == []

   def test_range_decreasing_negativestep(self):
      assert list(range(5, -2, -1)) == [5, 4, 3, 2, 1, 0 , -1]

   def test_range_posfencepost1(self):
       assert list(range(1, 10, 3)) == [1, 4, 7]

   def test_range_posfencepost2(self):
       assert list(range(1, 11, 3)) == [1, 4, 7, 10]

   def test_range_posfencepost3(self):
       assert list(range(1, 12, 3)) == [1, 4, 7, 10]

   def test_range_negfencepost1(self):
       assert list(range(-1, -10, -3)) == [-1, -4, -7]

   def test_range_negfencepost2(self):
       assert list(range(-1, -11, -3)) == [-1, -4, -7, -10]

   def test_range_negfencepost3(self):
       assert list(range(-1, -12, -3)) == [-1, -4, -7, -10]

   def test_range_decreasing_negativelargestep(self):
       assert list(range(5, -2, -3)) == [5, 2, -1]

   def test_range_increasing_positivelargestep(self):
       assert list(range(-5, 2, 3)) == [-5, -2, 1]

   def test_range_zerostep(self):
       raises(ValueError, range, 1, 5, 0)

   def test_range_float(self):
       raises(TypeError, range, 0.1)
       raises(TypeError, range, 0.1, 0)
       raises(TypeError, range, 0, 0.1)
       raises(TypeError, range, 0.1, 0, 0)
       raises(TypeError, range, 0, 0.1, 0)
       raises(TypeError, range, 0, 0, 0.1)

   def test_range_wrong_type(self):
       raises(TypeError, range, "42")

   def test_range_object_with___index__(self):
       class A(object):
           def __index__(self):
               return 5

       assert list(range(A())) == [0, 1, 2, 3, 4]
       assert list(range(0, A())) == [0, 1, 2, 3, 4]
       assert list(range(0, 10, A())) == [0, 5]

   def test_range_long(self):
       import sys
       assert list(range(-2**100)) == []
       assert list(range(0, -2**100)) == []
       assert list(range(0, 2**100, -1)) == []
       assert list(range(0, 2**100, -1)) == []

       a = 10 * sys.maxsize
       assert list(range(a, a+2)) == [a, a+1]
       assert list(range(a+2, a, -1)) == [a+2, a+1]
       assert list(range(a+4, a, -2)) == [a+4, a+2]
       assert list(range(a, a*5, a)) == [a, 2*a, 3*a, 4*a]

   def test_range_cases(self):
       import sys
       for start in [10, 10 * sys.maxsize]:
           for stop in [start-4, start-1, start, start+1, start+4]:
              for step in [1, 2, 3, 4]:
                  lst = list(range(start, stop, step))
                  expected = []
                  a = start
                  while a < stop:
                      expected.append(a)
                      a += step
                  assert lst == expected
              for step in [-1, -2, -3, -4]:
                  lst = list(range(start, stop, step))
                  expected = []
                  a = start
                  while a > stop:
                      expected.append(a)
                      a += step
                  assert lst == expected

   def test_range_contains(self):
      assert 3 in range(5)
      assert 3 not in range(3)
      assert 3 not in range(4, 5)
      assert 3 in range(1, 5, 2)
      assert 3 not in range(0, 5, 2)
      assert '3' not in range(5)

   def test_range_count(self):
      assert range(5).count(3) == 1
      assert type(range(5).count(3)) is int
      assert range(0, 5, 2).count(3) == 0
      assert range(5).count(3.0) == 1
      assert range(5).count('3') == 0

   def test_range_getitem(self):
      assert range(6)[3] == 3
      assert range(6)[-1] == 5
      raises(IndexError, range(6).__getitem__, 6)

   def test_range_slice(self):
      # range objects don't implement equality in 3.2, use the repr
      assert repr(range(6)[2:5]) == 'range(2, 5)'
      assert repr(range(6)[-1:-3:-2]) == 'range(5, 3, -2)'

   def test_large_range(self):
      import sys
      def _range_len(x):
         try:
            length = len(x)
         except OverflowError:
            step = x[1] - x[0]
            length = 1 + ((x[-1] - x[0]) // step)
            return length
         a = -sys.maxsize
         b = sys.maxsize
         expected_len = b - a
         x = range(a, b)
         assert a in x
         assert b not in x
         raises(OverflowError, len, x)
         assert _range_len(x) == expected_len
