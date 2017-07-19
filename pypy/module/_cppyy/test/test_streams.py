import py, os, sys


currpath = py.path.local(__file__).dirpath()
test_dct = str(currpath.join("std_streamsDict.so"))

def setup_module(mod):
    if sys.platform == 'win32':
        py.test.skip("win32 not supported so far")
    err = os.system("cd '%s' && make std_streamsDict.so" % currpath)
    if err:
        raise OSError("'make' failed (see stderr)")

class AppTestSTDStreams:
    spaceconfig = dict(usemodules=['_cppyy', '_rawffi', 'itertools'])

    def setup_class(cls):
        cls.w_test_dct  = cls.space.newtext(test_dct)
        cls.w_streams = cls.space.appexec([], """():
            import _cppyy
            return _cppyy.load_reflection_info(%r)""" % (test_dct, ))

    def test01_std_ostream(self):
        """Test availability of std::ostream"""

        import _cppyy

        assert _cppyy.gbl.std is _cppyy.gbl.std
        assert _cppyy.gbl.std.ostream is _cppyy.gbl.std.ostream

        assert callable(_cppyy.gbl.std.ostream)

    def test02_std_cout(self):
        """Test access to std::cout"""

        import _cppyy

        assert not (_cppyy.gbl.std.cout is None)
