import py, os, sys

# These tests are for the CINT backend only (they exercise ROOT features
# and classes that are not loaded/available with the Reflex backend). At
# some point, these tests are likely covered by the CLang/LLVM backend.
from pypy.module.cppyy import capi
if capi.identify() != 'CINT':
    py.test.skip("backend-specific: CINT-only tests")

# load _cffi_backend early, or its global vars are counted as leaks in the
# test (note that the module is not otherwise used in the test itself)
from pypy.module._cffi_backend import newtype

currpath = py.path.local(__file__).dirpath()
iotypes_dct = str(currpath.join("iotypesDict.so"))

def setup_module(mod):
    if sys.platform == 'win32':
        py.test.skip("win32 not supported so far")
    err = os.system("cd '%s' && make CINT=t iotypesDict.so" % currpath)
    if err:
        raise OSError("'make' failed (see stderr)")

class AppTestCINT:
    spaceconfig = dict(usemodules=['cppyy', '_rawffi', '_ffi', 'itertools'])

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


class AppTestCINTPYTHONIZATIONS:
    spaceconfig = dict(usemodules=['cppyy', '_rawffi', '_ffi', 'itertools'])

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

    def test04_TStringTObjString(self):
        """Test string/TString interchangebility"""

        import cppyy

        test = "aap noot mies"

        s1 = cppyy.gbl.TString(test )
        s2 = str(s1)

        assert s1 == test
        assert test == s2
        assert s1 == s2

        s3 = cppyy.gbl.TObjString(s2)
        assert s3 == test
        assert s2 == s3

        # force use of: TNamed(const TString &name, const TString &title)
        n = cppyy.gbl.TNamed(test, cppyy.gbl.TString("title"))
        assert n.GetTitle() == "title"
        assert n.GetName() == test


class AppTestCINTTTREE:
    spaceconfig = dict(usemodules=['cppyy', '_rawffi', '_ffi', 'itertools'])

    def setup_class(cls):
        cls.w_N = cls.space.wrap(5)
        cls.w_M = cls.space.wrap(10)
        cls.w_fname = cls.space.wrap("test.root")
        cls.w_tname = cls.space.wrap("test")
        cls.w_title = cls.space.wrap("test tree")
        cls.w_iotypes = cls.space.appexec([], """():
            import cppyy
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
        """Test writing of builtins"""

        from cppyy import gbl               # bootstraps, only needed for tests
        from cppyy.gbl import TFile, TTree
        from cppyy.gbl.std import vector

        f = TFile(self.fname, "RECREATE")
        mytree = TTree(self.tname, self.title)
        mytree._python_owns = False

        import array
        mytree.ba = array.array('c', [chr(0)])
        mytree.ia = array.array('i', [0])
        mytree.da = array.array('d', [0.])

        mytree.Branch("my_bool",   mytree.ba, "my_bool/O")
        mytree.Branch("my_int",    mytree.ia, "my_int/I")
        mytree.Branch("my_int2",   mytree.ia, "my_int2/I")
        mytree.Branch("my_double", mytree.da, "my_double/D")

        for i in range(self.N):
            # make sure value is different from default (0)
            mytree.ba[0] = i%2 and chr(0) or chr(1)
            mytree.ia[0] = i+1
            mytree.da[0] = (i+1)/2.
            mytree.Fill()
        f.Write()
        f.Close()

    def test08_read_builtin(self):
        """Test reading of builtins"""

        from cppyy import gbl
        from cppyy.gbl import TFile

        f = TFile(self.fname)
        mytree = f.Get(self.tname)

        raises(AttributeError, getattr, mytree, "does_not_exist")

        i = 1
        for event in mytree:
            assert event.my_bool   == (i-1)%2 and 0 or 1
            assert event.my_int    == i
            assert event.my_double == i/2.
            i += 1
        assert (i-1) == self.N

        f.Close()

    def test09_user_read_builtin(self):
        """Test user-directed reading of builtins"""

        from cppyy import gbl
        from cppyy.gbl import TFile

        f = TFile(self.fname)
        mytree = f.Get(self.tname)

        # note, this is an old, annoted tree from test08
        for i in range(3, mytree.GetEntriesFast()):
            mytree.GetEntry(i)
            assert mytree.my_int  == i+1
            assert mytree.my_int2 == i+1


class AppTestCINTREGRESSION:
    spaceconfig = dict(usemodules=['cppyy', '_rawffi', '_ffi', 'itertools'])

    # these are tests that at some point in the past resulted in failures on
    # PyROOT; kept here to confirm no regression from PyROOT

    def test01_regression(self):
        """TPaveText::AddText() used to result in KeyError"""

        # This is where the original problem was discovered, and the test is
        # left in. However, the detailed underlying problem, as well as the
        # solution to it, is tested in test_fragile.py

        from cppyy import gbl
        from cppyy.gbl import TPaveText

        hello = TPaveText( .1, .8, .9, .97 )
        hello.AddText( 'Hello, World!' )


class AppTestCINTFUNCTION:
    spaceconfig = dict(usemodules=['cppyy', '_rawffi', '_ffi', 'itertools'])

    # test the function callbacks; this does not work with Reflex, as it can
    # not generate functions on the fly (it might with cffi?)

    def test01_global_function_callback(self):
        """Test callback of a python global function"""

        import cppyy
        TF1 = cppyy.gbl.TF1

        def identity(x):
            return x[0]

        f = TF1("pyf1", identity, -1., 1., 0)

        assert f.Eval(0.5)  == 0.5
        assert f.Eval(-10.) == -10.
        assert f.Eval(1.0)  == 1.0

        # check proper propagation of default value
        f = TF1("pyf1d", identity, -1., 1.)

        assert f.Eval(0.5) == 0.5

    def test02_callable_object_callback(self):
        """Test callback of a python callable object"""

        import cppyy
        TF1 = cppyy.gbl.TF1

        class Linear:
            def __call__(self, x, par):
                return par[0] + x[0]*par[1]

        f = TF1("pyf2", Linear(), -1., 1., 2)
        f.SetParameters(5., 2.)

        assert f.Eval(-0.1) == 4.8
        assert f.Eval(1.3)  == 7.6

    def test03_fit_with_python_gaussian(self):
        """Test fitting with a python global function"""

        # note: this function is dread-fully slow when running testing un-translated

        import cppyy, math
        TF1, TH1F = cppyy.gbl.TF1, cppyy.gbl.TH1F

        def pygaus(x, par):
            arg1 = 0
            scale1 =0
            ddx = 0.01

            if (par[2] != 0.0):
                arg1 = (x[0]-par[1])/par[2]
                scale1 = (ddx*0.39894228)/par[2]
                h1 = par[0]/(1+par[3])

                gauss = h1*scale1*math.exp(-0.5*arg1*arg1)
            else:
                gauss = 0.
            return gauss

        f = TF1("pygaus", pygaus, -4, 4, 4)
        f.SetParameters(600, 0.43, 0.35, 600)

        h = TH1F("h", "test", 100, -4, 4)
        h.FillRandom("gaus", 200000)
        h.Fit(f, "0Q")

        assert f.GetNDF() == 96
        result = f.GetParameters()
        assert round(result[1] - 0., 1) == 0  # mean
        assert round(result[2] - 1., 1) == 0  # s.d.


class AppTestSURPLUS:
    spaceconfig = dict(usemodules=['cppyy', '_rawffi', '_ffi', 'itertools'])

    # these are tests that were historically exercised on ROOT classes and
    # have twins on custom classes; kept here just in case differences crop
    # up between the ROOT classes and the custom ones

    def test01_class_enum(self):
        """Test class enum access and values"""

        import cppyy
        TObject = cppyy.gbl.TObject
        gROOT = cppyy.gbl.gROOT

        assert TObject.kBitMask    == gROOT.ProcessLine("return TObject::kBitMask;")
        assert TObject.kIsOnHeap   == gROOT.ProcessLine("return TObject::kIsOnHeap;")
        assert TObject.kNotDeleted == gROOT.ProcessLine("return TObject::kNotDeleted;")
        assert TObject.kZombie     == gROOT.ProcessLine("return TObject::kZombie;")

        t = TObject()

        assert TObject.kBitMask    == t.kBitMask
        assert TObject.kIsOnHeap   == t.kIsOnHeap
        assert TObject.kNotDeleted == t.kNotDeleted
        assert TObject.kZombie     == t.kZombie

    def test02_global_enum(self):
        """Test global enums access and values"""

        import cppyy
        from cppyy import gbl

        assert gbl.kRed   == gbl.gROOT.ProcessLine("return kRed;")
        assert gbl.kGreen == gbl.gROOT.ProcessLine("return kGreen;")
        assert gbl.kBlue  == gbl.gROOT.ProcessLine("return kBlue;")

    def test03_copy_contructor(self):
        """Test copy constructor"""

        import cppyy
        TLorentzVector = cppyy.gbl.TLorentzVector

        t1 = TLorentzVector(1., 2., 3., -4.)
        t2 = TLorentzVector(0., 0., 0.,  0.)
        t3 = TLorentzVector(t1)

        assert t1 == t3
        assert t1 != t2

        for i in range(4):
            assert t1[i] == t3[i]

    def test04_object_validity(self):
        """Test object validity checking"""

        import cppyy

        t1 = cppyy.gbl.TObject()

        assert t1
        assert not not t1

        t2 = cppyy.gbl.gROOT.FindObject("Nah, I don't exist")

        assert not t2

    def test05_element_access(self):
        """Test access to elements in matrix and array objects."""

        from cppyy import gbl

        N = 3
        v = gbl.TVectorF(N)
        m = gbl.TMatrixD(N, N)

        for i in range(N):
            assert v[i] == 0.0

            for j in range(N):
                assert m[i][j] == 0.0

    def test06_static_function_call( self ):
        """Test call to static function."""

        import cppyy
        TROOT, gROOT = cppyy.gbl.TROOT, cppyy.gbl.gROOT

        c1 = TROOT.Class()
        assert not not c1

        c2 = gROOT.Class()

        assert c1 == c2

        old = gROOT.GetDirLevel()
        TROOT.SetDirLevel(2)
        assert 2 == gROOT.GetDirLevel()
        gROOT.SetDirLevel(old)

        old = TROOT.GetDirLevel()
        gROOT.SetDirLevel(3)
        assert 3 == TROOT.GetDirLevel()
        TROOT.SetDirLevel(old)

    def test07_macro(self):
        """Test access to cpp macro's"""

        from cppyy import gbl

        assert gbl.NULL == 0

        gbl.gROOT.ProcessLine('#define aap "aap"')
        gbl.gROOT.ProcessLine('#define noot 1')
        gbl.gROOT.ProcessLine('#define mies 2.0')

        # TODO: macro's assumed to always be of long type ...
        #assert gbl.aap  == "aap"
        assert gbl.noot == 1
        #assert gbl.mies == 2.0

    def test08_opaque_pointer_passing(self):
        """Test passing around of opaque pointers"""

        import cppyy

        # TODO: figure out CObject (see also test_advanced.py)

        s = cppyy.gbl.TString("Hello World!")
        #cobj = cppyy.as_cobject(s)
        addr = cppyy.addressof(s)

        #assert s == cppyy.bind_object(cobj, s.__class__)
        #assert s == cppyy.bind_object(cobj, "TString")
        assert s == cppyy.bind_object(addr, s.__class__)
        assert s == cppyy.bind_object(addr, "TString")

    def test09_object_and_pointer_comparisons(self):
        """Verify object and pointer comparisons"""

        import cppyy
        gbl = cppyy.gbl

        c1 = cppyy.bind_object(0, gbl.TCanvas)
        assert c1 == None
        assert None == c1

        c2 = cppyy.bind_object(0, gbl.TCanvas)
        assert c1 == c2
        assert c2 == c1

        # TLorentzVector overrides operator==
        l1 = cppyy.bind_object(0, gbl.TLorentzVector)
        assert l1 == None
        assert None == l1

        assert c1 != l1
        assert l1 != c1

        l2 = cppyy.bind_object(0, gbl.TLorentzVector)
        assert l1 == l2
        assert l2 == l1 

        l3 = gbl.TLorentzVector(1, 2, 3, 4)
        l4 = gbl.TLorentzVector(1, 2, 3, 4)
        l5 = gbl.TLorentzVector(4, 3, 2, 1)
        assert l3 == l4
        assert l4 == l3

        assert l3 != None                 # like this to ensure __ne__ is called
        assert None != l3                 # id.
        assert l3 != l5
        assert l5 != l3

    def test10_recursive_remove(self):
        """Verify that objects are recursively removed when destroyed"""

        import cppyy

        c = cppyy.gbl.TClass.GetClass("TObject")

        o = cppyy.gbl.TObject()
        assert o

        o.SetBit(cppyy.gbl.TObject.kMustCleanup)
        c.Destructor(o)
        assert not o
