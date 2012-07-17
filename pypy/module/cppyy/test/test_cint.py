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


class AppTestCINTPythonizations:
    def setup_class(cls):
        cls.space = space

    def test03_TVector(self):
        """Test TVector2/3/T behavior"""

        import cppyy, math

        N = 51

        # TVectorF is a typedef of floats
        v = cppyy.gbl.TVectorF(N)
        for i in range(N):
             v[i] = i*i

        assert len(v) == N
        for j in v:
             assert round(v[int(math.sqrt(j)+0.5)]-j, 5) == 0.


class AppTestCINTTTree:
    def setup_class(cls):
        cls.space = space
        cls.w_N = space.wrap(5)
        cls.w_M = space.wrap(10)
        cls.w_fname = space.wrap("test.root")
        cls.w_tname = space.wrap("test")
        cls.w_title = space.wrap("test tree")
        cls.space.appexec([], """():
            import cppyy""")

    def test01_write_stdvector( self ):
        """Test writing of a single branched TTree with an std::vector<double>"""

        from cppyy import gbl               # bootstraps, only needed for tests
        from cppyy.gbl import TFile, TTree
        from cppyy.gbl.std import vector

        f = TFile(self.fname, "RECREATE")
        t = TTree(self.tname, self.title)
        t._python_owns = False

        v = vector("double")()
        raises(TypeError, TTree.Branch, None, "mydata", v.__class__.__name__, v)
        raises(TypeError, TTree.Branch, v, "mydata", v.__class__.__name__, v)

        t.Branch("mydata", v.__class__.__name__, v)

        for i in range(self.N):
            for j in range(self.M):
                v.push_back(i*self.M+j)
            t.Fill()
            v.clear()
        f.Write()
        f.Close()

    def test02_read_stdvector(self):
        """Test reading of a single branched TTree with an std::vector<double>"""

        from cppyy import gbl               # bootstraps, only needed for tests
        from cppyy.gbl import TFile

        f = TFile(self.fname)
        mytree = f.Get(self.tname)

        i = 0
        for event in mytree:
            for entry in mytree.mydata:
                assert i == int(entry)
                i += 1
        assert i == self.N * self.M

        f.Close()
