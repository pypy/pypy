import autopath

class AppTestZip:

   def test_zip_no_arguments(self):
      import sys
      if sys.version_info < (2,4):
          # Test 2.3 behaviour
          raises(TypeError, zip)
          return
      # Test 2.4 behaviour
      assert zip() ==  []
      assert zip(*[]) == []
   
   def test_one_list(self):
      assert zip([1, 2, 3]) == [(1,), (2,), (3,)]

   def test_three_lists_same_size(self):
      assert zip([1, 2, 3], [3, 4, 5], [6, 7, 8]) == (
                        [(1, 3, 6), (2, 4, 7), (3, 5, 8)])

   def test_three_lists_different_sizes(self):
      assert zip([1, 2], [3, 4, 5, 6], [6, 7, 8]) == (
                        [(1, 3, 6), (2, 4, 7)])

   def test_tuples(self):
      assert zip((1, 2, 3)) == [(1,), (2,), (3,)]

   def test_string(self):
      assert zip('hello') == [('h',), ('e',), ('l',), ('l',), ('o',)]

   def test_strings(self):
      assert zip('hello', 'bye') == (
                       [('h', 'b'), ('e', 'y'), ('l', 'e')])

   def test_mixed_types(self):
      assert zip('hello', [1,2,3,4], (7,8,9,10)) == (
                       [('h', 1, 7), ('e', 2, 8), ('l', 3, 9), ('l', 4, 10)])
