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

    def test01_simple_inheritence(self):
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

    def test02_namespaces(self):
        """Test access to namespaces and inner classes"""

        import cppyy

# TODO: have Reflex add the globals to the dictionary ...
#        assert cppyy.gbl.a_ns.g_a                           == 11
        assert cppyy.gbl.a_ns.b_class.s_b                   == 22
        assert cppyy.gbl.a_ns.b_class().m_b                 == -2
        assert cppyy.gbl.a_ns.b_class.c_class.s_c           == 33
        assert cppyy.gbl.a_ns.b_class.c_class().m_c         == -3
#        assert cppyy.gbl.a_ns.d_ns.g_d                      == 44
        assert cppyy.gbl.a_ns.d_ns.e_class.s_e              == 55
        assert cppyy.gbl.a_ns.d_ns.e_class().m_e            == -5
        assert cppyy.gbl.a_ns.d_ns.e_class.f_class.s_f      == 66
        assert cppyy.gbl.a_ns.d_ns.e_class.f_class().m_f    == -6

        assert cppyy.gbl.a_ns      is cppyy.gbl.a_ns
        assert cppyy.gbl.a_ns.d_ns is cppyy.gbl.a_ns.d_ns

        assert cppyy.gbl.a_ns.b_class              is cppyy.gbl.a_ns.b_class
        assert cppyy.gbl.a_ns.d_ns.e_class         is cppyy.gbl.a_ns.d_ns.e_class
        assert cppyy.gbl.a_ns.d_ns.e_class.f_class is cppyy.gbl.a_ns.d_ns.e_class.f_class
