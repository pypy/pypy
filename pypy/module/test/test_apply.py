import testsupport
from pypy.module.builtin_app import apply, min, max

def myminmax(*arr, **dict):
   # trivial function which has the signature *args, **kw
   v = list(arr) + dict.values()
   return min(v), max(v)
  
class TestApply(testsupport.TestCase):

   def setUp(self):
      pass
  
   def tearDown(self):
      pass

# This is a very trivial series of tests.  If apply is subtlely broken,
# we will have to find out some other way.
      
   def test_trivial_listonly(self):
      self.assertEqual(apply(myminmax,
                             [-1,-2,-3,-4]),
                             (-4, -1))

   def test_trivial_dictonly(self):
      self.assertEqual(apply(myminmax,
                             [], {'null' : 0, 'one': 1, 'two' : 2}),
                             (0, 2))
   def test_trivial(self):
      self.assertEqual(apply(myminmax,
                             [-1,-2,-3,-4],
                             {'null' : 0, 'one': 1, 'two' : 2}),
                             (-4, 2))

if __name__ == '__main__':
    testsupport.main()


