import testsupport

from pypy.interpreter.unittest_w
from pypy.objspace.std import StdObjSpace

class TestCompile(unittest_w.TestCase_w):

   def setUp(self):
      self.space = StdObjSpace()

   def tearDown(self):
      pass
      
if __name__ == '__main__':
    unittest.main()
 
