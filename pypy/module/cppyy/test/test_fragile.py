import py, os, sys
from pypy.conftest import gettestobjspace


currpath = py.path.local(__file__).dirpath()
shared_lib = str(currpath.join("fragileDict.so"))

space = gettestobjspace(usemodules=['cppyy'])

def setup_module(mod):
    if sys.platform == 'win32':
        py.test.skip("win32 not supported so far")
    err = os.system("cd '%s' && make fragileDict.so" % currpath)
    if err:
        raise OSError("'make' failed (see stderr)")

class AppTestSTL:
    def setup_class(cls):
        cls.space = space
        env = os.environ
        cls.w_shared_lib = space.wrap(shared_lib)
        cls.w_datatypes = cls.space.appexec([], """():
            import cppyy
            return cppyy.load_lib(%r)""" % (shared_lib, ))

    def test01_load_failure(self):
        """Test failure to load dictionary"""

        import cppyy
        raises(RuntimeError, cppyy.load_lib, "does_not_exist.so")

    def test02_missing_classes(self):
        """Test (non-)access to missing classes"""

        import cppyy

        raises(AttributeError, getattr, cppyy.gbl, "no_such_class")

        assert cppyy.gbl.fragile == cppyy.gbl.fragile
        fragile = cppyy.gbl.fragile

        raises(AttributeError, getattr, fragile, "no_such_class")

        assert fragile.B == fragile.B
        assert fragile.B().check() == ord('B')

        raises(NotImplementedError, fragile.B().gime_no_such)
