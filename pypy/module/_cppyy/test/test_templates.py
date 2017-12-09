import py, os, sys
from .support import setup_make


currpath = py.path.local(__file__).dirpath()
test_dct = str(currpath.join("templatesDict.so"))

def setup_module(mod):
    setup_make("templatesDict.so")

class AppTestTEMPLATES:
    spaceconfig = dict(usemodules=['_cppyy', '_rawffi', 'itertools'])

    def setup_class(cls):
        cls.w_test_dct  = cls.space.newtext(test_dct)
        cls.w_datatypes = cls.space.appexec([], """():
            import ctypes
            return ctypes.CDLL(%r, ctypes.RTLD_GLOBAL)""" % (test_dct, ))

    def test01_template_member_functions(self):
        """Template member functions lookup and calls"""

        import _cppyy

        m = _cppyy.gbl.MyTemplatedMethodClass()

        return

      # pre-instantiated
        assert m.get_size['char']()   == m.get_char_size()
        assert m.get_size[int]()      == m.get_int_size()

      # specialized
        assert m.get_size[long]()     == m.get_long_size()

      # auto-instantiation
        assert m.get_size[float]()    == m.get_float_size()
        assert m.get_size['double']() == m.get_double_size()
        assert m.get_size['MyTemplatedMethodClass']() == m.get_self_size()

      # auto through typedef
        assert m.get_size['MyTMCTypedef_t']() == m.get_self_size()
