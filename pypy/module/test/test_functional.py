import autopath
from pypy.tool import test


class TestMap(test.AppTestCase):

   def test_trivial_map_one_seq(self):
      self.assertEqual(map(lambda x: x+2, [1, 2, 3, 4]), [3, 4, 5, 6])

   def test_trivial_map_two_seq(self):
      self.assertEqual(map(lambda x,y: x+y, 
                           [1, 2, 3, 4],[1, 2, 3, 4]),
                       [2, 4, 6, 8])

   def test_trivial_map_sizes_dont_match_and_should(self):
      self.assertRaises(TypeError, map, lambda x,y: x+y, [1, 2, 3, 4], [1, 2, 3])

   def test_trivial_map_no_arguments(self):
      self.assertRaises(TypeError, map)
      
   def test_trivial_map_no_function_no_seq(self):
      self.assertRaises(TypeError, map, None)

   def test_trivial_map_no_fuction_one_seq(self):
      self.assertEqual(map(None, [1, 2, 3]), [1, 2, 3])
      
   def test_trivial_map_no_function(self):
      self.assertEqual(map(None, [1,2,3], [4,5,6], [7,8], [1]),
                       [(1, 4, 7, 1), (2, 5, 8, None), (3, 6, None, None)])
                       
   def test_map_identity1(self):
      a = ['1', 2, 3, 'b', None]
      b = a[:]
      self.assertEqual(map(lambda x: x, a), a)
      self.assertEqual(a, b)
 
   def test_map_None(self):
      a = ['1', 2, 3, 'b', None]
      b = a[:]
      self.assertEqual(map(None, a), a)
      self.assertEqual(a, b)

   def test_map_badoperation(self):
      a = ['1', 2, 3, 'b', None]
      self.assertRaises(TypeError, map, lambda x: x+1, a)

   def test_map_multiply_identity(self):
      a = ['1', 2, 3, 'b', None]
      b = [ 2, 3, 4, 5, 6]
      self.assertEqual(map(None, a, b), [('1', 2), (2, 3), (3, 4), ('b', 5), (None, 6)])

   def test_map_multiply(self):
      a = [1, 2, 3, 4]
      b = [0, 1, 1, 1]
      self.assertEqual(map(lambda x, y: x+y, a, b), [1, 2, 4, 5])

   def test_map_multiply(self):
      a = [1, 2, 3, 4, 5]
      b = []
      self.assertEqual(map(lambda x, y: x, a, b), a)

class TestZip(test.AppTestCase):
   def test_one_list(self):
      self.assertEqual(zip([1,2,3]), [(1,), (2,), (3,)])

   def test_three_lists(self):
      self.assertEqual(zip([1,2,3], [1,2], [1,2,3]), [(1,1,1), (2,2,2)])

class TestReduce(test.TestCase):
   def test_None(self):
       self.assertRaises(TypeError, reduce, lambda x, y: x+y, [1,2,3], None)

   def test_sum(self):
       self.assertEqual(reduce(lambda x, y: x+y, [1,2,3,4], 0), 10)
       self.assertEqual(reduce(lambda x, y: x+y, [1,2,3,4]), 10)
   
   def test_minus(self):
       self.assertEqual(reduce(lambda x, y: x-y, [10, 2, 8]), 0)
       self.assertEqual(reduce(lambda x, y: x-y, [2, 8], 10), 0)

class TestFilter(test.AppTestCase):
   def test_None(self):
       self.assertEqual(filter(None, ['a', 'b', 1, 0, None]), ['a', 'b', 1])

   def test_return_type(self):
       txt = "This is a test text"
       self.assertEqual(filter(None, txt), txt)
       tup = ("a", None, 0, [], 1)
       self.assertEqual(filter(None, tup), ("a", 1))
       
   def test_function(self):
       self.assertEqual(filter(lambda x: x != "a", "a small text"), " smll text")

if __name__ == '__main__':
    test.main()


