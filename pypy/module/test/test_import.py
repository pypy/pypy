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


if __name__ == '__main__':
    testit.main()


