import autopath
from pypy.tool import testit
from pypy.interpreter import gateway
import os


def _setup(dn=os.path.abspath(os.path.join(os.path.dirname(__file__), 'impsubdir'))):
    import sys
    sys.path.append(dn)
    return sys.modules.copy()

_setup = gateway.app2interp(_setup,'setup')

def _teardown(saved_modules):
    import sys
    sys.path.pop()
    sys.modules.clear()
    sys.modules.update(saved_modules)

_teardown = gateway.app2interp(_teardown,'teardown')

class TestImport(testit.AppTestCase):

    def setUp(self): # interpreter-level
        testit.AppTestCase.setUp(self)
        self.saved_modules = _setup(self.space)

    def tearDown(self): # interpreter-level
        _teardown(self.space,self.saved_modules) 

    def test_import_bare_dir_fails(self):
        def imp():
           import notapackage
        self.assertRaises(ImportError,imp)

    def test_import_sys(self):
        import sys

    def test_import_a(self):
        import sys
        import a
        self.assertEquals(a, sys.modules.get('a'))

    def test_import_a_cache(self):
        import sys
        import a
        a0 = a
        import a
        self.assertEquals(a, a0)

    def test_import_pkg(self):
        import sys
        import pkg
        self.assertEquals(pkg, sys.modules.get('pkg'))

    def test_import_dotted(self):
        import sys
        import pkg.a
        self.assertEquals(pkg, sys.modules.get('pkg'))
        self.assertEquals(pkg.a, sys.modules.get('pkg.a'))

    def test_import_dotted_cache(self):
        import sys
        import pkg.a
        self.assertEquals(pkg, sys.modules.get('pkg'))
        self.assertEquals(pkg.a, sys.modules.get('pkg.a'))
        pkg0 = pkg
        pkg_a0 = pkg.a
        import pkg.a
        self.assertEquals(pkg, pkg0)
        self.assertEquals(pkg.a, pkg_a0)

    def test_import_dotted2(self):
        import sys
        import pkg.pkg1.a
        self.assertEquals(pkg, sys.modules.get('pkg'))
        self.assertEquals(pkg.pkg1, sys.modules.get('pkg.pkg1'))
        self.assertEquals(pkg.pkg1.a, sys.modules.get('pkg.pkg1.a'))

    def test_import_ambig(self):
        import sys
        import ambig
        self.assertEquals(ambig, sys.modules.get('ambig'))
        self.assert_(hasattr(ambig,'imapackage'))

    def test_from_a(self):
        import sys
        from a import imamodule
        self.assert_('a' in sys.modules)
        self.assertEquals(imamodule, 1)

    def test_from_dotted(self):
        import sys
        from pkg.a import imamodule
        self.assert_('pkg' in sys.modules)
        self.assert_('pkg.a' in sys.modules)
        self.assertEquals(imamodule, 1)

    def test_from_pkg_import_module(self):
        import sys
        from pkg import a
        self.assert_('pkg' in sys.modules)
        self.assert_('pkg.a' in sys.modules)
        pkg = sys.modules.get('pkg')
        self.assertEquals(a, pkg.a)
        aa = sys.modules.get('pkg.a')
        self.assertEquals(a, aa)

    def test_import_relative(self):
        from pkg import relative_a
        self.assertEquals(relative_a.a.inpackage,1)

    def test_import_relative_back_to_absolute(self):
        from pkg import abs_b
        self.assertEquals(abs_b.b.inpackage,0)
        import sys
        self.assertEquals(sys.modules.get('pkg.b'),None)

    def test_import_pkg_relative(self):
        import pkg_relative_a
        self.assertEquals(pkg_relative_a.a.inpackage,1)

    def test_import_relative_partial_success(self):
        def imp():
            import pkg_r.inpkg
        self.assertRaises(ImportError,imp)

    def test_import_relative_back_to_absolute2(self):
        from pkg import abs_x_y
        import sys
        self.assertEquals(abs_x_y.x.__name__,'x')
        self.assertEquals(abs_x_y.x.y.__name__,'x.y')
        # grrr
        self.assertEquals(sys.modules.get('pkg.x'),None)
        self.assert_('pkg.x.y' not in sys.modules)
        
        
        
if __name__ == '__main__':
    testit.main()
