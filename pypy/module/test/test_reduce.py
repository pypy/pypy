import autopath

class AppTestReduce:
   def test_None(self):
       raises(TypeError, reduce, lambda x, y: x+y, [1,2,3], None)

   def test_sum(self):
       assert reduce(lambda x, y: x+y, [1,2,3,4], 0) == 10
       assert reduce(lambda x, y: x+y, [1,2,3,4]) == 10
   
   def test_minus(self):
       assert reduce(lambda x, y: x-y, [10, 2, 8]) == 0
       assert reduce(lambda x, y: x-y, [2, 8], 10) == 0
