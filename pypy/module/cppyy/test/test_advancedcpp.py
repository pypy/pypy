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

        b = base_class()
        assert isinstance(b, base_class)
        assert not isinstance(b, derived_class)

        assert b.get_value()      == 1
        assert b.get_base_value() == 1.1

        d = derived_class()
        assert isinstance(d, derived_class)
        assert isinstance(d, base_class)

        assert d.get_value()         == 2
        assert d.get_base_value()    == 1.1
        assert d.get_derived_value() == 2.2

        d.destruct()

    def test02_namespaces(self):
        """Test access to namespaces and inner classes"""

        import cppyy
        gbl = cppyy.gbl

        assert gbl.a_ns.g_a                           == 11
        assert gbl.a_ns.b_class.s_b                   == 22
        assert gbl.a_ns.b_class().m_b                 == -2
        assert gbl.a_ns.b_class.c_class.s_c           == 33
        assert gbl.a_ns.b_class.c_class().m_c         == -3
        assert gbl.a_ns.d_ns.g_d                      == 44
        assert gbl.a_ns.d_ns.e_class.s_e              == 55
        assert gbl.a_ns.d_ns.e_class().m_e            == -5
        assert gbl.a_ns.d_ns.e_class.f_class.s_f      == 66
        assert gbl.a_ns.d_ns.e_class.f_class().m_f    == -6

        assert gbl.a_ns      is gbl.a_ns
        assert gbl.a_ns.d_ns is gbl.a_ns.d_ns

        assert gbl.a_ns.b_class              is gbl.a_ns.b_class
        assert gbl.a_ns.d_ns.e_class         is gbl.a_ns.d_ns.e_class
        assert gbl.a_ns.d_ns.e_class.f_class is gbl.a_ns.d_ns.e_class.f_class

    def test03_template_types(self):
        """Test bindings of templated types"""

        import cppyy
        gbl = cppyy.gbl

        assert gbl.T1 is gbl.T1
        assert gbl.T2 is gbl.T2
        assert gbl.T3 is gbl.T3
        assert not gbl.T1 is gbl.T2
        assert not gbl.T2 is gbl.T3

        assert gbl.T1('int') is gbl.T1('int')
        assert gbl.T1(int)   is gbl.T1('int')
        assert gbl.T2('T1<int>')     is gbl.T2('T1<int>')
        assert gbl.T2(gbl.T1('int')) is gbl.T2('T1<int>')
        assert gbl.T3('int,double')    is gbl.T3('int,double')
        assert gbl.T3('int', 'double') is gbl.T3('int,double')
        assert gbl.T3(int, 'double')   is gbl.T3('int,double')
        assert gbl.T3('T1<int>,T2<T1<int> >') is gbl.T3('T1<int>,T2<T1<int> >')
        assert gbl.T3('T1<int>', gbl.T2(gbl.T1(int))) is gbl.T3('T1<int>,T2<T1<int> >')

        assert gbl.a_ns.T4(int) is gbl.a_ns.T4('int')
        assert gbl.a_ns.T4('a_ns::T4<T3<int,double> >')\
               is gbl.a_ns.T4(gbl.a_ns.T4(gbl.T3(int, 'double')))

        t1 = gbl.T1(int)()
        assert t1.m_t1    == 1
        assert t1.value() == 1
        t1.destruct()

        t1 = gbl.T1(int)(11)
        assert t1.m_t1    == 11
        assert t1.value() == 11
        t1.m_t1 = 111
        assert t1.value() == 111
        t1.destruct()

    def test04_instantiation(self):
        """Test non-instatiatability of abstract classes"""

        import cppyy
   
        raises(TypeError, cppyy.gbl.a_class)
        raises(TypeError, cppyy.gbl.some_abstract_class)

