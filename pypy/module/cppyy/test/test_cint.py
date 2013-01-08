import py, os, sys

# These tests are for the CINT backend only (they exercise ROOT features
# and classes that are not loaded/available with the Reflex backend). At
# some point, these tests are likely covered by the CLang/LLVM backend.
from pypy.module.cppyy import capi
if capi.identify() != 'CINT':
    py.test.skip("backend-specific: CINT-only tests")

currpath = py.path.local(__file__).dirpath()
iotypes_dct = str(currpath.join("iotypesDict.so"))

def setup_module(mod):
    if sys.platform == 'win32':
        py.test.skip("win32 not supported so far")
    err = os.system("cd '%s' && make CINT=t iotypesDict.so" % currpath)
    if err:
        raise OSError("'make' failed (see stderr)")

class AppTestCINT:
    spaceconfig = dict(usemodules=['cppyy'])

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

        proxy = cppyy.gbl.__class__.__dict__['gDebug']
        cppyy.gbl.gDebug = 3
        assert proxy.__get__(proxy, None) == 3

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

        proxy = cppyy.gbl.__class__.__dict__['gMyOwnGlobal']
        assert proxy.__get__(proxy, None) == 3.1415

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
    spaceconfig = dict(usemodules=['cppyy'])

    def test01_strings(self):
        """Test TString/TObjString compatibility"""

        import cppyy

        pyteststr = "aap noot mies"
        def test_string(s1, s2):
            assert len(s1) == len(s2)
            assert s1 == s1
            assert s1 == s2
            assert s1 == str(s1)
            assert s1 == pyteststr
            assert s1 != "aap"
            assert s1 != ""
            assert s1 < "noot"
            assert repr(s1) == repr(s2)

        s1 = cppyy.gbl.TString(pyteststr)
        test_string(s1, pyteststr)

        s3 = cppyy.gbl.TObjString(pyteststr)
        test_string(s3, pyteststr)

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
    spaceconfig = dict(usemodules=['cppyy', 'array', '_rawffi', '_cffi_backend'])

    def setup_class(cls):
        cls.w_N = cls.space.wrap(5)
        cls.w_M = cls.space.wrap(10)
        cls.w_fname = cls.space.wrap("test.root")
        cls.w_tname = cls.space.wrap("test")
        cls.w_title = cls.space.wrap("test tree")
        cls.w_iotypes = cls.space.appexec([], """():
            import cppyy, _cffi_backend
            _cffi_backend.new_primitive_type      # prevents leak-checking complaints on _cffi_backend
            return cppyy.load_reflection_info(%r)""" % (iotypes_dct,))

    def test01_write_stdvector(self):
        """Test writing of a single branched TTree with an std::vector<double>"""

        from cppyy import gbl               # bootstraps, only needed for tests
        from cppyy.gbl import TFile, TTree
        from cppyy.gbl.std import vector

        f = TFile(self.fname, "RECREATE")
        mytree = TTree(self.tname, self.title)
        mytree._python_owns = False

        v = vector("double")()
        raises(TypeError, TTree.Branch, None, "mydata", v.__class__.__name__, v)
        raises(TypeError, TTree.Branch, v, "mydata", v.__class__.__name__, v)

        mytree.Branch("mydata", v.__class__.__name__, v)

        for i in range(self.N):
            for j in range(self.M):
                v.push_back(i*self.M+j)
            mytree.Fill()
            v.clear()
        f.Write()
        f.Close()

    def test02_file_open(self):

        from cppyy import gbl

        f = gbl.TFile.Open(self.fname)
        s = str(f)            # should not raise
        r = repr(f)

        f.Close()

    def test03_read_stdvector(self):
        """Test reading of a single branched TTree with an std::vector<double>"""

        from cppyy import gbl
        from cppyy.gbl import TFile

        f = TFile(self.fname)
        mytree = f.Get(self.tname)

        i = 0
        for event in mytree:
            assert len(event.mydata) == self.M
            for entry in event.mydata:
                assert i == int(entry)
                i += 1
        assert i == self.N * self.M

        f.Close()

    def test04_write_some_data_object(self):
        """Test writing of a complex data object"""

        from cppyy import gbl
        from cppyy.gbl import TFile, TTree, IO
        from cppyy.gbl.IO import SomeDataObject

        f = TFile(self.fname, "RECREATE")
        mytree = TTree(self.tname, self.title)

        d = SomeDataObject()
        b = mytree.Branch("data", d)
        mytree._python_owns = False
        assert b

        for i in range(self.N):
            for j in range(self.M):
                d.add_float(i*self.M+j)
            d.add_tuple(d.get_floats())

            mytree.Fill()

        f.Write()
        f.Close()

    def test05_read_some_data_object(self):
        """Test reading of a complex data object"""

        from cppyy import gbl
        from cppyy.gbl import TFile

        f = TFile(self.fname)
        mytree = f.Get(self.tname)

        j = 1
        for event in mytree:
            i = 0
            assert len(event.data.get_floats()) == j*self.M
            for entry in event.data.get_floats():
                assert i == int(entry)
                i += 1

            k = 1
            assert len(event.data.get_tuples()) == j
            for mytuple in event.data.get_tuples():
                i = 0
                assert len(mytuple) == k*self.M
                for entry in mytuple:
                    assert i == int(entry)
                    i += 1
                k += 1
            j += 1
        assert j-1 == self.N
        #
        f.Close()

    def test06_branch_activation(self):
        """Test of automatic branch activation"""

        from cppyy import gbl
        from cppyy.gbl import TFile, TTree
        from cppyy.gbl.std import vector

        L = 5

        # writing
        f = TFile(self.fname, "RECREATE")
        mytree = TTree(self.tname, self.title)
        mytree._python_owns = False

        for i in range(L):
            v = vector("double")()
            mytree.Branch("mydata_%d"%i, v.__class__.__name__, v)
            mytree.__dict__["v_%d"%i] = v

        for i in range(self.N):
            for k in range(L):
                v = mytree.__dict__["v_%d"%k]
                for j in range(self.M):
                    mytree.__dict__["v_%d"%k].push_back(i*self.M+j*L+k)
            mytree.Fill()
            for k in range(L):
                v = mytree.__dict__["v_%d"%k]
                v.clear()
        f.Write()
        f.Close()

        del mytree, f
        import gc
        gc.collect()

        # reading
        f = TFile(self.fname)
        mytree = f.Get(self.tname)

        # force (initial) disabling of all branches
        mytree.SetBranchStatus("*",0);

        i = 0
        for event in mytree:
            for k in range(L):
                j = 0
                data = getattr(mytree, "mydata_%d"%k)
                assert len(data) == self.M
                for entry in data:
                    assert entry == i*self.M+j*L+k
                    j += 1
                assert j == self.M
            i += 1
        assert i == self.N

    def test07_write_builtin(self):
        """Test writing of a builtins"""

        from cppyy import gbl               # bootstraps, only needed for tests
        from cppyy.gbl import TFile, TTree
        from cppyy.gbl.std import vector

        f = TFile(self.fname, "RECREATE")
        mytree = TTree(self.tname, self.title)
        mytree._python_owns = False

        import array
        a = array.array('i', [0])
        b = array.array('d', [0.])

        mytree.Branch("myi", a, "myi/I")
        mytree.Branch("myd", b, "myd/D")

        for i in range(self.N):
            a[0] = i
            b[0] = i/2.
            mytree.Fill()
        f.Write()
        f.Close()

    def test08_read_builtin(self):
        """Test reading of a single branched TTree with an std::vector<double>"""

        from cppyy import gbl
        from cppyy.gbl import TFile

        f = TFile(self.fname)
        mytree = f.Get(self.tname)

        i = 0
        for event in mytree:
            assert event.myi == i
            assert event.myd == i/2.
            i += 1
        assert i == self.N

        f.Close()


class AppTestRegression:
    spaceconfig = dict(usemodules=['cppyy'])

    def test01_regression(self):
        """TPaveText::AddText() used to result in KeyError"""

        # This is where the original problem was discovered, and the test is
        # left in. However, the detailed underlying problem, as well as the
        # solution to it, is tested in test_fragile.py

        from cppyy import gbl
        from cppyy.gbl import TPaveText

        hello = TPaveText( .1, .8, .9, .97 )
        hello.AddText( 'Hello, World!' )
