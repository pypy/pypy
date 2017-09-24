import py, os, sys


currpath = py.path.local(__file__).dirpath()

def setup_module(mod):
    if sys.platform == 'win32':
        py.test.skip("win32 not supported so far")
    err = os.system("cd '%s' && make example01Dict.so" % currpath)
    if err:
        raise OSError("'make' failed (see stderr)")


class AppTestACLASSLOADER:
    spaceconfig = dict(usemodules=['_cppyy', '_rawffi', 'itertools'])

    def setup_class(cls):
        cls.space.appexec([], """():
            import _cppyy""")

    def test01_class_autoloading(self):
        """Test whether a class can be found through .rootmap."""
        import _cppyy
        example01_class = _cppyy.gbl.example01
        assert example01_class
        cl2 = _cppyy.gbl.example01
        assert cl2
        assert example01_class is cl2
