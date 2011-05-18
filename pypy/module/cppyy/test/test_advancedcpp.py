import py, os, sys
from pypy.conftest import gettestobjspace


currpath = py.path.local(__file__).dirpath()
shared_lib = str(currpath.join("advancedcppDict.so"))

space = gettestobjspace(usemodules=['cppyy'])

def setup_module(mod):
    if sys.platform == 'win32':
        py.test.skip("win32 not supported so far")
    err = os.system("cd '%s' && make advancedcppDict.so" % currpath)
    if err:
        raise OSError("'make' failed (see stderr)")

class AppTestADVANCEDCPP:
    def setup_class(cls):
        cls.space = space
        env = os.environ
        cls.w_shared_lib = space.wrap(shared_lib)
        cls.w_datatypes = cls.space.appexec([], """():
            import cppyy
            return cppyy.load_lib(%r)""" % (shared_lib, ))

    def test1_simple_inheritence(self):
        """Test binding of a basic inheritance structure"""

        import cppyy
        base_class    = cppyy.gbl.base_class
        derived_class = cppyy.gbl.derived_class

        assert issubclass(derived_class, base_class)
        assert not issubclass(base_class, derived_class)

        c = derived_class()
        assert isinstance( c, derived_class )
        assert isinstance( c, base_class )

        c.destruct()
