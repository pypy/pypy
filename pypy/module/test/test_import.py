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
        self.assertEquals(a, sys.modules.get('a'))

    def test_import_bare_dir_fails(self):
        def imp():
           import impsubdir
        self.assertRaises(ImportError,imp)

    def test_import_pkg(self):
        import sys
        sys.path.append('impsubdir')
        import pkg
        self.assertEquals(pkg, sys.modules.get('pkg'))

    def test_import_dotted(self):
        import sys
        sys.path.append('impsubdir')
        import pkg.a
        self.assertEquals(pkg, sys.modules.get('pkg'))
        self.assertEquals(pkg.a, sys.modules.get('pkg.a'))

    def test_import_dotted2(self):
        import sys
        sys.path.append('impsubdir')
        import pkg.pkg1.a
        self.assertEquals(pkg, sys.modules.get('pkg'))
        self.assertEquals(pkg.pkg1, sys.modules.get('pkg.pkg1'))
        self.assertEquals(pkg.pkg1.a, sys.modules.get('pkg.pkg1.a'))

    def test_import_ambig(self):
        import sys
        sys.path.append('impsubdir')
        import ambig
        self.assertEquals(ambig, sys.modules.get('ambig'))
        self.assert_(hasattr(ambig,'imapackage'))

    def test_from_a(self):
        import sys
        sys.path.append('impsubdir')
        from a import imamodule
        self.assert_('a' in sys.modules)
        self.assertEquals(imamodule, 1)

    def test_from_dotted(self):
        import sys
        sys.path.append('impsubdir')
        from pkg.a import imamodule
        self.assert_('pkg' in sys.modules)
        self.assert_('pkg.a' in sys.modules)
        self.assertEquals(imamodule, 1)

    def test_from_pkg_import_module(self):
        import sys
        sys.path.append('impsubdir')
        from pkg import a
        self.assert_('pkg' in sys.modules)
        self.assert_('pkg.a' in sys.modules)
        pkg = sys.modules.get('pkg')
        self.assertEquals(a, pkg.a)
        aa = sys.modules.get('pkg.a')
        self.assertEquals(a, aa)

    def test_import_relative(self):
        import sys
        sys.path.append('impsubdir')
        from pkg import relative_a
        self.assertEquals(relative_a.a.inpackage,1)
        
if __name__ == '__main__':
    testit.main()
