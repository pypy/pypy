import autopath
from pypy.tool import testit

class TestReduce(testit.AppTestCase):
   def test_None(self):
       self.assertRaises(TypeError, reduce, lambda x, y: x+y, [1,2,3], None)

   def test_sum(self):
       self.assertEqual(reduce(lambda x, y: x+y, [1,2,3,4], 0), 10)
       self.assertEqual(reduce(lambda x, y: x+y, [1,2,3,4]), 10)
   
   def test_minus(self):
       self.assertEqual(reduce(lambda x, y: x-y, [10, 2, 8]), 0)
       self.assertEqual(reduce(lambda x, y: x-y, [2, 8], 10), 0)

if __name__ == '__main__':
    testit.main()


