import autopath

class AppTestRange:

   def test_range_toofew(self):
      raises(TypeError, range)

   def test_range_toomany(self):
      raises(TypeError, range,  1, 2, 3, 4)

   def test_range_one(self):
      assert range(1) == [0]

   def test_range_posstartisstop(self):
      assert range(1, 1) == []

   def test_range_negstartisstop(self):
      assert range(-1, -1) == []

   def test_range_zero(self):
      assert range(0) == []

   def test_range_twoargs(self):
      assert range(1, 2) == [1]
      
   def test_range_decreasingtwoargs(self):
      assert range(3, 1) == []

   def test_range_negatives(self):
      assert range(-3) == []

   def test_range_decreasing_negativestep(self):
      assert range(5, -2, -1) == [5, 4, 3, 2, 1, 0 , -1]

   def test_range_posfencepost1(self):
       assert range (1, 10, 3) == [1, 4, 7]

   def test_range_posfencepost2(self):
       assert range (1, 11, 3) == [1, 4, 7, 10]

   def test_range_posfencepost3(self):
       assert range (1, 12, 3) == [1, 4, 7, 10]

   def test_range_negfencepost1(self):
       assert range (-1, -10, -3) == [-1, -4, -7]

   def test_range_negfencepost2(self):
       assert range (-1, -11, -3) == [-1, -4, -7, -10]

   def test_range_negfencepost3(self):
       assert range (-1, -12, -3) == [-1, -4, -7, -10]

   def test_range_decreasing_negativelargestep(self):
       assert range(5, -2, -3) == [5, 2, -1]

   def test_range_increasing_positivelargestep(self):
       assert range(-5, 2, 3) == [-5, -2, 1]

   def test_range_zerostep(self):
       raises(ValueError, range, 1, 5, 0)

   def test_range_float(self):
       "How CPython does it - UGLY."
       assert range(0.1, 2.0, 1.1) == [0, 1]

   def test_range_wrong_type(self):
       raises(TypeError, range, "42")

   def test_range_object_with___int__(self):
       class A(object):
           def __int__(self):
               return 5

       assert range(A()) == [0, 1, 2, 3, 4]
       assert range(0, A()) == [0, 1, 2, 3, 4]
       assert range(0, 10, A()) == [0, 5]

   def test_range_long(self):
       import sys
       assert range(-2**100) == []
       assert range(0, -2**100) == []
       assert range(0, 2**100, -1) == []
       assert range(0, 2**100, -1) == []

       a = long(10 * sys.maxint)
       b = long(100 * sys.maxint)
       c = long(50 * sys.maxint)

       assert range(a, a+2) == [a, a+1]
       assert range(a+2, a, -1L) == [a+2, a+1]
       assert range(a+4, a, -2) == [a+4, a+2]
 
