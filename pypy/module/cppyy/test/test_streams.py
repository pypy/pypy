import py, os, sys
from pypy.conftest import gettestobjspace


currpath = py.path.local(__file__).dirpath()
test_dct = str(currpath.join("std_streamsDict.so"))

space = gettestobjspace(usemodules=['cppyy'])

def setup_module(mod):
    if sys.platform == 'win32':
        py.test.skip("win32 not supported so far")
    err = os.system("cd '%s' && make std_streamsDict.so" % currpath)
    if err:
        raise OSError("'make' failed (see stderr)")

class AppTestSTDStreams:
    def setup_class(cls):
        cls.space = space
        env = os.environ
        cls.w_N = space.wrap(13)
        cls.w_test_dct  = space.wrap(test_dct)
        cls.w_datatypes = cls.space.appexec([], """():
            import cppyy
            return cppyy.load_reflection_info(%r)""" % (test_dct, ))

    def test01_std_ostream(self):
        """Test access to an std::vector<int>"""

        import cppyy

        assert cppyy.gbl.std is cppyy.gbl.std
        assert cppyy.gbl.std.ostream is cppyy.gbl.std.ostream

        assert callable(cppyy.gbl.std.ostream)

