import testsupport
from pypy.module.builtin_app import map, filter, reduce, zip

class TestMap(testsupport.TestCase):

   def test_map_identity1(self):
      a = ['1', 2, 3, 'b', None]
      b = a[:]
      self.assertEqual(map(lambda x: x, a), a)
      self.assertEqual(a, b)
 
   def test_map_None1(self):
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

class TestZip(testsupport.TestCase):
   pass
      
if __name__ == '__main__':
    testsupport.main()


