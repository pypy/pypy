import py, os, sys
from pypy.conftest import gettestobjspace


currpath = py.path.local(__file__).dirpath()
shared_lib = str(currpath.join("stltypesDict.so"))

space = gettestobjspace(usemodules=['cppyy'])

def setup_module(mod):
    if sys.platform == 'win32':
        py.test.skip("win32 not supported so far")
    err = os.system("cd '%s' && make stltypesDict.so" % currpath)
    if err:
        raise OSError("'make' failed (see stderr)")

class AppTestSTL:
    def setup_class(cls):
        cls.space = space
        env = os.environ
        cls.w_N = space.wrap(13)
        cls.w_shared_lib = space.wrap(shared_lib)
        cls.w_datatypes = cls.space.appexec([], """():
            import cppyy
            return cppyy.load_lib(%r)""" % (shared_lib, ))

    def test1BuiltinTypeVectorType( self ):
        """Test access to an std::vector<int>"""

        import cppyy

        assert cppyy.gbl.std        is cppyy.gbl.std
        assert cppyy.gbl.std.vector is cppyy.gbl.std.vector

        assert callable(cppyy.gbl.std.vector)

        tv1 = getattr(cppyy.gbl.std,'vector<int>')
        tv2 = cppyy.gbl.std.vector('int')

        assert tv1 is tv2

        #-----
        v = tv1(self.N)
        for i in range(self.N):
          #  v[i] = i
          #  assert v[i] == i
          #  assert v.at(i) == i
            pass

        assert v.size() == self.N
        assert len(v) == self.N
        v.destruct()

        #-----
        v = tv1()
        for i in range(self.N):
            v.push_back(i)
            assert v.size() == i+1
            assert v.at(i) == i
            assert v[i] == i

        assert v.size() == self.N
        assert len(v) == self.N
        v.destruct()
