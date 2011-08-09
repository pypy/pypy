import py, os, sys
from pypy.conftest import gettestobjspace


currpath = py.path.local(__file__).dirpath()
test_dct = str(currpath.join("advancedcppDict.so"))

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
        cls.w_test_dct  = space.wrap(test_dct)
        cls.w_datatypes = cls.space.appexec([], """():
            import cppyy
            return cppyy.load_reflection_info(%r)""" % (test_dct, ))

    def test01_default_arguments(self):
        """Test usage of default arguments"""

        import cppyy
        defaulter = cppyy.gbl.defaulter

        d = defaulter()
        assert d.m_a == 11
        assert d.m_b == 22
        assert d.m_c == 33
        d.destruct()

        d = defaulter(0)
        assert d.m_a ==  0
        assert d.m_b == 22
        assert d.m_c == 33
        d.destruct()

        d = defaulter(1, 2)
        assert d.m_a ==  1
        assert d.m_b ==  2
        assert d.m_c == 33
        d.destruct()

        d = defaulter(3, 4, 5)
        assert d.m_a ==  3
        assert d.m_b ==  4
        assert d.m_c ==  5
        d.destruct()

    def test02_simple_inheritance(self):
        """Test binding of a basic inheritance structure"""

        import cppyy
        base_class    = cppyy.gbl.base_class
        derived_class = cppyy.gbl.derived_class

        assert issubclass(derived_class, base_class)
        assert not issubclass(base_class, derived_class)

        b = base_class()
        assert isinstance(b, base_class)
        assert not isinstance(b, derived_class)

        assert b.m_b              == 1
        assert b.get_value()      == 1
        assert b.m_db             == 1.1
        assert b.get_base_value() == 1.1

        b.m_b, b.m_db = 11, 11.11
        assert b.m_b              == 11
        assert b.get_value()      == 11
        assert b.m_db             == 11.11
        assert b.get_base_value() == 11.11

        b.destruct()

        d = derived_class()
        assert isinstance(d, derived_class)
        assert isinstance(d, base_class)

        assert d.m_d                 == 2
        assert d.get_value()         == 2
        assert d.m_dd                == 2.2
        assert d.get_derived_value() == 2.2

        assert d.m_b                 == 1
        assert d.m_db                == 1.1
        assert d.get_base_value()    == 1.1

        d.m_b, d.m_db = 11, 11.11
        d.m_d, d.m_dd = 22, 22.22

        assert d.m_d                 == 22
        assert d.get_value()         == 22
        assert d.m_dd                == 22.22
        assert d.get_derived_value() == 22.22

        assert d.m_b                 == 11
        assert d.m_db                == 11.11
        assert d.get_base_value()    == 11.11

        d.destruct()

    def test03_namespaces(self):
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

    def test04_template_types(self):
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
        assert gbl.T2(gbl.T1(int)) is gbl.T2('T1<int>')
        assert gbl.T3('int,double')    is gbl.T3('int,double')
        assert gbl.T3('int', 'double') is gbl.T3('int,double')
        assert gbl.T3(int, 'double')   is gbl.T3('int,double')
        assert gbl.T3('T1<int>,T2<T1<int> >') is gbl.T3('T1<int>,T2<T1<int> >')
        assert gbl.T3('T1<int>', gbl.T2(gbl.T1(int))) is gbl.T3('T1<int>,T2<T1<int> >')

        assert gbl.a_ns.T4(int) is gbl.a_ns.T4('int')
        assert gbl.a_ns.T4('a_ns::T4<T3<int,double> >')\
               is gbl.a_ns.T4(gbl.a_ns.T4(gbl.T3(int, 'double')))

        #-----
        t1 = gbl.T1(int)()
        assert t1.m_t1    == 1
        assert t1.value() == 1
        t1.destruct()

        #-----
        t1 = gbl.T1(int)(11)
        assert t1.m_t1    == 11
        assert t1.value() == 11
        t1.m_t1 = 111
        assert t1.value() == 111
        assert t1.m_t1    == 111
        t1.destruct()

        #-----
        t2 = gbl.T2(gbl.T1(int))(gbl.T1(int)(32))
        t2.m_t2.m_t1 = 32
        assert t2.m_t2.value() == 32
        assert t2.m_t2.m_t1    == 32
        t2.destruct()

    def test05_abstract_classes(self):
        """Test non-instatiatability of abstract classes"""

        import cppyy
        gbl = cppyy.gbl

        raises(TypeError, gbl.a_class)
        raises(TypeError, gbl.some_abstract_class)

        assert issubclass(gbl.some_concrete_class, gbl.some_abstract_class)

        c = gbl.some_concrete_class()
        assert isinstance(c, gbl.some_concrete_class)
        assert isinstance(c, gbl.some_abstract_class)

    def test06_data_members(self):
        """Test data member access when using virtual inheritence"""

        import cppyy
        a_class   = cppyy.gbl.a_class
        b_class   = cppyy.gbl.b_class
        c_class_1 = cppyy.gbl.c_class_1
        c_class_2 = cppyy.gbl.c_class_2
        d_class   = cppyy.gbl.d_class

        assert issubclass(b_class, a_class)
        assert issubclass(c_class_1, a_class)
        assert issubclass(c_class_1, b_class)
        assert issubclass(c_class_2, a_class)
        assert issubclass(c_class_2, b_class)
        assert issubclass(d_class, a_class)
        assert issubclass(d_class, b_class)
        assert issubclass(d_class, c_class_2)

        #-----
        b = b_class()
        assert b.m_a          == 1
        assert b.m_da         == 1.1
        assert b.m_b          == 2
        assert b.m_db         == 2.2

        b.m_a = 11
        assert b.m_a          == 11
        assert b.m_b          == 2

        b.m_da = 11.11
        assert b.m_da         == 11.11
        assert b.m_db         == 2.2

        b.m_b = 22
        assert b.m_a          == 11
        assert b.m_da         == 11.11
        assert b.m_b          == 22
      # assert b.get_value()  == 22

        b.m_db = 22.22
        assert b.m_db         == 22.22

        b.destruct()

        #-----
        c1 = c_class_1()
        assert c1.m_a         == 1
        assert c1.m_b         == 2
        assert c1.m_c         == 3

        c1.m_a = 11
        assert c1.m_a         == 11

        c1.m_b = 22
        assert c1.m_a         == 11
        assert c1.m_b         == 22

        c1.m_c = 33
        assert c1.m_a         == 11
        assert c1.m_b         == 22
        assert c1.m_c         == 33
      # assert c1.get_value() == 33

        c1.destruct()

        #-----
        d = d_class()
        assert d.m_a          == 1
        assert d.m_b          == 2
        assert d.m_c          == 3
        assert d.m_d          == 4

        d.m_a = 11
        assert d.m_a          == 11

        d.m_b = 22
        assert d.m_a          == 11
        assert d.m_b          == 22

        d.m_c = 33
        assert d.m_a          == 11
        assert d.m_b          == 22
        assert d.m_c          == 33

        d.m_d = 44
        assert d.m_a          == 11
        assert d.m_b          == 22
        assert d.m_c          == 33
        assert d.m_d          == 44
      # assert d.get_value()  == 44

        d.destruct()

    def test07_pass_by_reference(self):
        """Test reference passing when using virtual inheritance"""

        import cppyy
        gbl = cppyy.gbl
        b_class = gbl.b_class
        c_class = gbl.c_class_2
        d_class = gbl.d_class

        #-----
        b = b_class()
        b.m_a, b.m_b = 11, 22
        assert gbl.get_a(b) == 11
        assert gbl.get_b(b) == 22
        b.destruct()

        #-----
        c = c_class()
        c.m_a, c.m_b, c.m_c = 11, 22, 33
        assert gbl.get_a(c) == 11
        assert gbl.get_b(c) == 22
        assert gbl.get_c(c) == 33
        c.destruct()

        #-----
        d = d_class()
        d.m_a, d.m_b, d.m_c, d.m_d = 11, 22, 33, 44
        assert gbl.get_a(d) == 11
        assert gbl.get_b(d) == 22
        assert gbl.get_c(d) == 33
        assert gbl.get_d(d) == 44
        d.destruct()
