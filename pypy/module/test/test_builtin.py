import testsupport
from pypy.module.builtin_app import cmp


class TestBuiltin(testsupport.TestCase):

   def setUp(self):
      self.space = testsupport.objspace()

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
      self.assertWRaises_w(s.w_ValueError,
                           w_chr,
                           w(-1))
      self.assertWRaises_w(s.w_TypeError,
                           w_chr,
                           w('a'))

   def test_import(self):
       s = self.space      
       w = s.wrap
       w_import = self.get_builtin('__import__')
       w_dict = s.newdict([])
       w_fromlist = s.newlist([])
       # finding a module to import is an odd game; quopri is
       # sufficiently simple
       s.call_function(w_import, w('quopri'), w_dict, w_dict, w_fromlist)
     
class TestCmp(testsupport.TestCase):
   
    def test_cmp(self):
       self.failUnless(cmp(9, 9) == 0)
       self.failUnless(cmp(0,9) < 0)
       self.failUnless(cmp(9,0) > 0)
 
if __name__ == '__main__':
    testsupport.main()
 
