import autopath

from pypy.tool import testit

# This is a very trivial series of tests.  If apply is subtlely broken,
# we will have to find out some other way.
  
class TestApply(testit.AppTestCase):

   def test_trivial_listonly(self):
      def mymin(*args):
           return min(list(args))

      self.assertEqual(apply(mymin, [-1,-2,-3,-4]), -4)

   def test_trivial_dictonly(self):
      def mymin(*arr, **kwargs):
           return min(list(arr) + kwargs.values())
      self.assertEqual(apply(mymin,
                             [], {'null' : 0, 'one': 1, 'two' : 2}),
                             0)
   def test_trivial(self):
      def mymin(*arr, **kwargs):
           return min(list(arr) + kwargs.values())
      self.assertEqual(apply(mymin,
                             [-1,-2,-3,-4],
                             {'null' : 0, 'one': 1, 'two' : 2}),
                             (-4))

if __name__ == '__main__':
    testit.main()


