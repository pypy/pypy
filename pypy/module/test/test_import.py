import autopath
from pypy.tool import testit

class TestImport(testit.AppTestCase):

   def setUp(self): # interpreter-level
      self.space = testit.new_objspace()

   def test_import_sys(self):
      import sys

   def test_import_a(self):
      import sys
      sys.path.append('impsubdir')
      import a
      self.assert_('a' in sys.modules)

   def test_import_bare_dir_fails(self):
      def imp():
         import impsubdir
      self.assertRaises(ImportError,imp)

   def test_import_pkg(self):
      import sys
      sys.path.append('impsubdir')
      import pkg
      self.assert_('pkg' in sys.modules)

   def test_import_dotted(self):
      import sys
      sys.path.append('impsubdir')
      import pkg.a
      self.assert_('pkg' in sys.modules)
      self.assert_('pkg.a' in sys.modules)

   def test_import_dotted2(self):
      import sys
      sys.path.append('impsubdir')
      import pkg.pkg1.a
      self.assert_('pkg' in sys.modules)
      self.assert_('pkg.pkg1' in sys.modules)
      self.assert_('pkg.pkg1.a' in sys.modules)
      
if __name__ == '__main__':
    testit.main()


