import testsupport
from pypy.module.builtin_app import range

class TestRange(testsupport.TestCase):

   def setUp(self):
      pass

   def tearDown(self):
      pass

   def test_range_one(self):
      self.assertEqual(range(1), [0])

   def test_range_none(self):
      self.assertEqual(range(0), [])

   def test_range_twoargs(self):
      self.assertEqual(range(1, 2), [1])
      
   def test_range_decreasingtwoargs(self):
      self.assertEqual(range(3, 1), [])

   def test_range_negatives(self):
      self.assertEqual(range(-3), [])

   def test_range_decreasing_negativestep(self):
      self.assertEqual(range(5, -2, -1), [5, 4, 3, 2, 1, 0 , -1])

   def test_range_decreasing_negativelargestep(self):
      self.assertEqual(range(5, -2, -3), [5, 2, -1])

   def test_range_decreasing_negativelargestep2(self):
      self.assertEqual(range(5, -3, -3), [5, 2, -1])

   def test_range_zerostep(self):
      self.assertRaises(ValueError, range, 1, 5, 0)

   def XXXtest_range_float(self):
      "How CPython does it - UGLY, ignored for now."
      self.assertEqual(range(0.1, 2.0, 1.1), [0, 1])
      
if __name__ == '__main__':
    testsupport.main()


