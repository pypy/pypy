import testsupport

import unittest

from pypy.interpreter import unittest_w
from pypy.objspace.std import StdObjSpace

class TestCompile(unittest_w.TestCase_w):

   def setUp(self):
      self.space = StdObjSpace()

   def tearDown(self):
      pass

   def get_builtin(self, name):
      s = self.space
      w_name = s.wrap(name)
      w_bltin = s.getitem(s.w_builtins, w_name)
      return w_bltin

   def test_chr(self):
      s = self.space      
      w = s.wrap
      w_chr = self.get_builtin('chr')
      self.assertEqual_w(w(chr(65)),
                         s.call_function(w_chr, w(65)))
      
if __name__ == '__main__':
    unittest.main()
 
