import autopath
from pypy.module.builtin_app import zip
from pypy.tool import test

class TestZip(test.TestCase):

   def test_zip_no_arguments(self):
      self.assertRaises(TypeError, zip)

   def test_one_list(self):
      self.assertEqual(zip([1, 2, 3]), [(1,), (2,), (3,)])

   def test_three_lists_same_size(self):
      self.assertEqual(zip([1, 2, 3], [3, 4, 5], [6, 7, 8]),
                        [(1, 3, 6), (2, 4, 7), (3, 5, 8)])

   def test_three_lists_different_sizes(self):
      self.assertEqual(zip([1, 2], [3, 4, 5, 6], [6, 7, 8]),
                        [(1, 3, 6), (2, 4, 7)])

   def test_tuples(self):
      self.assertEqual(zip((1, 2, 3)), [(1,), (2,), (3,)])

   def test_string(self):
      self.assertEqual(zip('hello'), [('h',), ('e',), ('l',), ('l',), ('o',)])

   def test_strings(self):
      self.assertEqual(zip('hello', 'bye'),
                       [('h', 'b'), ('e', 'y'), ('l', 'e')])

   def test_mixed_types(self):
      self.assertEqual(zip('hello', [1,2,3,4], (7,8,9,10)),
                       [('h', 1, 7), ('e', 2, 8), ('l', 3, 9), ('l', 4, 10)])

if __name__ == '__main__':
    test.main()


