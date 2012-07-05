import py, os, sys
from pypy.conftest import gettestobjspace

# These tests are for the CINT backend only (they exercise ROOT features
# and classes that are not loaded/available with the Reflex backend). At
# some point, these tests are likely covered by the CLang/LLVM backend.
from pypy.module.cppyy import capi
if capi.identify() != 'CINT':
    py.test.skip("backend-specific: CINT-only tests")

space = gettestobjspace(usemodules=['cppyy'])

class AppTestCINT:
    def setup_class(cls):
        cls.space = space

    def test01_globals(self):
        """Test the availability of ROOT globals"""

        import cppyy

        assert cppyy.gbl.gROOT
        assert cppyy.gbl.gApplication
        assert cppyy.gbl.gSystem
        assert cppyy.gbl.TInterpreter.Instance()           # compiled
        assert cppyy.gbl.TInterpreter                      # interpreted
        assert cppyy.gbl.TDirectory.CurrentDirectory()     # compiled
        assert cppyy.gbl.TDirectory                        # interpreted

    def test02_write_access_to_globals(self):
        """Test overwritability of ROOT globals"""

        import cppyy

        oldval = cppyy.gbl.gDebug
        assert oldval != 3

        proxy = cppyy.gbl.__class__.gDebug
        cppyy.gbl.gDebug = 3
        assert proxy.__get__(proxy) == 3

        # this is where this test differs from test03_write_access_to_globals
        # in test_pythonify.py
        cppyy.gbl.gROOT.ProcessLine('int gDebugCopy = gDebug;')
        assert cppyy.gbl.gDebugCopy == 3

        cppyy.gbl.gDebug = oldval

    def test03_create_access_to_globals(self):
        """Test creation and access of new ROOT globals"""

        import cppyy

        cppyy.gbl.gROOT.ProcessLine('double gMyOwnGlobal = 3.1415')
        assert cppyy.gbl.gMyOwnGlobal == 3.1415

        proxy = cppyy.gbl.__class__.gMyOwnGlobal
        assert proxy.__get__(proxy) == 3.1415

    def test04_auto_loading(self):
        """Test auto-loading by retrieving a non-preloaded class"""

        import cppyy

        l = cppyy.gbl.TLorentzVector()
        assert isinstance(l, cppyy.gbl.TLorentzVector)

    def test05_macro_loading(self):
        """Test accessibility to macro classes"""

        import cppyy

        loadres = cppyy.gbl.gROOT.LoadMacro('simple_class.C')
        assert loadres == 0

        base = cppyy.gbl.MySimpleBase
        simple = cppyy.gbl.MySimpleDerived
        simple_t = cppyy.gbl.MySimpleDerived_t

        assert issubclass(simple, base)
        assert simple is simple_t

        c = simple()
        assert isinstance(c, simple)
        assert c.m_data == c.get_data()

        c.set_data(13)
        assert c.m_data == 13
        assert c.get_data() == 13
