import testsupport
from pypy.module.builtin_app import map

# trivial functions for testing 

def add_two(x):
   return x + 2

def add_both(x, y):
   return x + y

def add_both_with_none(x, y):
   if y is None:
      y = 1000
   return x + y

class TestMap(testsupport.TestCase):

   def test_trivial_map_no_arguments(self):
      self.assertRaises(TypeError, map)
      
   def test_trivial_map_no_function_no_seq(self):
      self.assertRaises(TypeError, map, None)

   def test_trivial_map_no_fuction_one_seq(self):
      self.assertEqual(map(None, [1, 2, 3]), [1, 2, 3])
      
   def test_trivial_map_no_function(self):
      # test that None padding works
      self.assertEqual(map(None, [1,2,3], [4,5,6], [7,8], [1]),
                       [(1, 4, 7, 1), (2, 5, 8, None), (3, 6, None, None)])

   def test_trivial_map_one_seq(self):
      self.assertEqual(map(add_two, [1, 2, 3, 4]), [3, 4, 5, 6])

   def test_trivial_map_two_seq(self):
      self.assertEqual(map(add_both, [1, 2, 3, 4],[1, 2, 3, 4]), [2, 4, 6, 8])

   def test_trivial_map_sizes_dont_match_None_padded_unhappy(self):
      # Test that None padding works, making add_both unhappy
      self.assertRaises(TypeError, map, add_both, [1, 2, 3, 4], [1, 2, 3])

   def test_trivial_map_sizes_dont_match_None_padded_happy(self):
      # Test that None padding works, more work for add_both_with_none
      self.assertEqual(map(add_both_with_none, [1, 2, 3, 4], [1, 2, 3]),
                       [2, 4, 6, 1004])

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

if __name__ == '__main__':
    testsupport.main()


