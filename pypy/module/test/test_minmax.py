import testsupport
from pypy.module.builtin_app import min, max

class TestMin(testsupport.TestCase):

   def setUp(self):
      pass

   def tearDown(self):
      pass

   def test_min_notseq(self):
      self.assertRaises(TypeError, min, 1)

   def test_min_usual(self):
      self.assertEqual(min(1, 2, 3), 1)

   def test_min_floats(self):
      self.assertEqual(min(0.1, 2.7, 14.7), 0.1)

   # write fixed point if that becomes a type.

   def test_min_chars(self):
      self.assertEqual(min('a', 'b', 'c'), 'a')

   # write a unicode test when unicode works.

   def test_min_strings(self):
      self.assertEqual(min('aaa', 'bbb', 'c'), 'aaa')

   # write an imaginary test when we have complex numbers
   
   def test_min_mixed(self):
      self.assertEqual(min('1', 2, 3, 'aa'), 2)

   def test_min_noargs(self):
      self.assertRaises(TypeError, min)

   def test_min_empty(self):
      self.assertRaises(ValueError, min, [])

class TestMax(testsupport.TestCase):

   def setUp(self):
      pass

   def tearDown(self):
      pass

   def test_max_notseq(self):
      self.assertRaises(TypeError, max, 1)

   def test_max_usual(self):
      self.assertEqual(max(1, 2, 3), 3)

   def test_max_floats(self):
      self.assertEqual(max(0.1, 2.7, 14.7), 14.7)

   # write fixed point if that becomes a type.

   def test_max_chars(self):
      self.assertEqual(max('a', 'b', 'c'), 'c')

   # write a unicode test when unicode works.

   def test_max_strings(self):
      self.assertEqual(max('aaa', 'bbb', 'c'), 'c')

   # write an imaginary test when we have complex numbers
   
   def test_max_mixed(self):
      self.assertEqual(max('1', 2, 3, 'aa'), 'aa')

   def test_max_noargs(self):
      self.assertRaises(TypeError, max)

   def test_max_empty(self):
      self.assertRaises(ValueError, max, [])

if __name__ == '__main__':
    testsupport.main()
