import py, os, sys
from pypy.conftest import gettestobjspace


currpath = py.path.local(__file__).dirpath()
shared_lib = str(currpath.join("datatypesDict.so"))

space = gettestobjspace(usemodules=['cppyy', 'array'])

def setup_module(mod):
    if sys.platform == 'win32':
        py.test.skip("win32 not supported so far")
    err = os.system("cd '%s' && make datatypesDict.so" % currpath)
    if err:
        raise OSError("'make' failed (see stderr)")

class AppTestDATATYPES:
    def setup_class(cls):
        cls.space = space
        env = os.environ
        cls.w_N = space.wrap(5)    # should be imported from the dictionary
        cls.w_shared_lib = space.wrap(shared_lib)
        cls.w_datatypes = cls.space.appexec([], """():
            import cppyy
            return cppyy.load_lib(%r)""" % (shared_lib, ))

    def test0_load_lib_cache(self):
        """Test whether loading a library twice results in the same object."""
        import cppyy
        lib2 = cppyy.load_lib(self.shared_lib)
        assert self.datatypes is lib2

    def test1_instance_data_read_access(self):
        """Test read access to instance public data and verify values"""

        import cppyy, sys
        cppyy_test_data = cppyy.gbl.cppyy_test_data

        c = cppyy_test_data()
        assert isinstance(c, cppyy_test_data)

        # reading boolean type
        assert c.m_bool == False

        # reading char types
        assert c.m_char  == 'a'
        assert c.m_uchar == 'c'

        # reading integer types
        assert c.m_short  == -11
        assert c.m_ushort ==  11
        assert c.m_int    == -22
        assert c.m_uint   ==  22
        assert c.m_long   == -33
        assert c.m_ulong  ==  33

        # reading floating point types
        assert round(c.m_float  + 44., 5) == 0
        assert round(c.m_double + 55., 8) == 0

        # reding of array types
        for i in range(self.N):
            # reading of integer array types
            assert c.m_short_array[i]       ==  -1*i
            assert c.get_short_array()[i]   ==  -1*i
            assert c.m_short_array2[i]      ==  -2*i
            assert c.get_short_array2()[i]  ==  -2*i
            assert c.m_ushort_array[i]      ==   3*i
            assert c.get_ushort_array()[i]  ==   3*i
            assert c.m_ushort_array2[i]     ==   4*i
            assert c.get_ushort_array2()[i] ==   4*i
            assert c.m_int_array[i]         ==  -5*i
            assert c.get_int_array()[i]     ==  -5*i
            assert c.m_int_array2[i]        ==  -6*i
            assert c.get_int_array2()[i]    ==  -6*i
            assert c.m_uint_array[i]        ==   7*i
            assert c.get_uint_array()[i]    ==   7*i
            assert c.m_uint_array2[i]       ==   8*i
            assert c.get_uint_array2()[i]   ==   8*i

            assert c.m_long_array[i]        ==  -9*i
            assert c.get_long_array()[i]    ==  -9*i
            assert c.m_long_array2[i]       == -10*i
            assert c.get_long_array2()[i]   == -10*i
            assert c.m_ulong_array[i]       ==  11*i
            assert c.get_ulong_array()[i]   ==  11*i
            assert c.m_ulong_array2[i]      ==  12*i
            assert c.get_ulong_array2()[i]  ==  12*i

            assert round(c.m_float_array[i]   + 13.*i, 5) == 0
            assert round(c.m_float_array2[i]  + 14.*i, 5) == 0
            assert round(c.m_double_array[i]  + 15.*i, 8) == 0
            assert round(c.m_double_array2[i] + 16.*i, 8) == 0

        # out-of-bounds checks
        raises(IndexError, c.m_short_array.__getitem__,  self.N)
        raises(IndexError, c.m_ushort_array.__getitem__, self.N)
        raises(IndexError, c.m_int_array.__getitem__,    self.N)
        raises(IndexError, c.m_uint_array.__getitem__,   self.N)
        raises(IndexError, c.m_long_array.__getitem__,   self.N)
        raises(IndexError, c.m_ulong_array.__getitem__,  self.N)
        raises(IndexError, c.m_float_array.__getitem__,  self.N)
        raises(IndexError, c.m_double_array.__getitem__, self.N)

        c.destruct()

    def test2_instance_data_write_access(self):
        """Test write access to instance public data and verify values"""

        import cppyy, sys
        cppyy_test_data = cppyy.gbl.cppyy_test_data

        c = cppyy_test_data()
        assert isinstance(c, cppyy_test_data)

        # boolean types through functions
        c.set_bool(True);
        assert c.get_bool() == True
        c.set_bool(0);     assert c.get_bool() == False

        # boolean types through data members
        c.m_bool = True;   assert c.get_bool() == True
        c.set_bool(True);  assert c.m_bool     == True
        c.m_bool = 0;      assert c.get_bool() == False
        c.set_bool(0);     assert c.m_bool     == False

        raises(TypeError, 'c.set_bool(10)')

        # char types through functions
        c.set_char('c');   assert c.get_char()  == 'c'
        c.set_uchar('e');  assert c.get_uchar() == 'e'

        # char types through data members
        c.m_char = 'b';    assert c.get_char()  ==     'b'
        c.m_char = 40;     assert c.get_char()  == chr(40)
        c.set_char('c');   assert c.m_char      ==     'c'
        c.set_char(41);    assert c.m_char      == chr(41)
        c.m_uchar = 'd';   assert c.get_uchar() ==     'd'
        c.m_uchar = 42;    assert c.get_uchar() == chr(42)
        c.set_uchar('e');  assert c.m_uchar     ==     'e'
        c.set_uchar(43);   assert c.m_uchar     == chr(43)

        raises(TypeError, 'c.set_char("string")')
        raises(TypeError, 'c.set_char(500)')
        raises(TypeError, 'c.set_uchar("string")')
# TODO: raises(TypeError, 'c.set_uchar(-1)')

        # integer types
        names = ['short', 'ushort', 'int', 'uint', 'long', 'ulong']
        for i in range(len(names)):
            exec 'c.m_%s = %d' % (names[i],i)
            assert eval('c.get_%s()' % names[i]) == i

        for i in range(len(names)):
            exec 'c.set_%s = %d' % (names[i],2*i)
            assert eval('c.m_%s' % names[i]) == i

        # float types through functions
        c.set_float( 0.123 );  assert round(c.get_float()  - 0.123, 5) == 0
        c.set_double( 0.456 ); assert round(c.get_double() - 0.456, 8) == 0

        # float types through data members
        c.m_float = 0.123;     assert round(c.get_float()  - 0.123, 5) == 0
        c.set_float( 0.234 );  assert round(c.m_float      - 0.234, 5) == 0
        c.m_double = 0.456;    assert round(c.get_double() - 0.456, 8) == 0
        c.set_double( 0.567 ); assert round(c.m_double     - 0.567, 8) == 0

        # arrays; there will be pointer copies, so destroy the current ones
        c.destroy_arrays()

        # integer arrays
        import array
        a = range(self.N)
        atypes = ['h', 'H', 'i', 'I', 'l', 'L' ]
        for j in range(len(names)):
            b = array.array(atypes[j], a)
            exec 'c.m_%s_array = b' % names[j]   # buffer copies
            for i in range(self.N):
                assert eval('c.m_%s_array[i]' % names[j]) == b[i]

            exec 'c.m_%s_array2 = b' % names[j]  # pointer copies
            b[i] = 28
            for i in range(self.N):
                assert eval('c.m_%s_array2[i]' % names[j]) == b[i]

        c.destruct()

    def test3_class_read_access(self):
        """Test read access to class public data and verify values"""

        import cppyy, sys
        cppyy_test_data = cppyy.gbl.cppyy_test_data

        c = cppyy_test_data()
        assert isinstance(c, cppyy_test_data)

        # char types
        assert cppyy_test_data.s_char  == 's'
        assert c.s_char                == 's'
        assert c.s_uchar               == 'u'
        assert cppyy_test_data.s_uchar == 'u'

        # integer types
        assert cppyy_test_data.s_short  == -101
        assert c.s_short                == -101
        assert c.s_ushort               ==  255
        assert cppyy_test_data.s_ushort ==  255
        assert cppyy_test_data.s_int    == -202
        assert c.s_int                  == -202
        assert c.s_uint                 ==  202
        assert cppyy_test_data.s_uint   ==  202
        assert cppyy_test_data.s_long   == -303L
        assert c.s_long                 == -303L
        assert c.s_ulong                ==  303L
        assert cppyy_test_data.s_ulong  ==  303L

        # floating point types
        assert round(cppyy_test_data.s_float  + 404., 5) == 0
        assert round(c.s_float                + 404., 5) == 0
        assert round(cppyy_test_data.s_double + 505., 8) == 0
        assert round(c.s_double               + 505., 8) == 0

        c.destruct()

    def test4_class_data_write_access(self):
        """Test write access to class public data and verify values"""

        import cppyy, sys
        cppyy_test_data = cppyy.gbl.cppyy_test_data

        c = cppyy_test_data()
        assert isinstance(c, cppyy_test_data)

        # char types
        cppyy_test_data.s_char          = 'a'
        assert c.s_char                == 'a'
        c.s_char                        = 'b'
        assert cppyy_test_data.s_char  == 'b'
        cppyy_test_data.s_uchar         = 'c'
        assert c.s_uchar               == 'c'
        c.s_uchar                       = 'd'
        assert cppyy_test_data.s_uchar == 'd'
        raises(TypeError, setattr, cppyy_test_data, 's_uchar', -1)
        raises(TypeError, setattr, c,               's_uchar', -1)

        # integer types
        c.s_short                        = -102
        assert cppyy_test_data.s_short  == -102
        cppyy_test_data.s_short          = -203
        assert c.s_short                == -203
        c.s_ushort                       =  127
        assert cppyy_test_data.s_ushort ==  127
        cppyy_test_data.s_ushort         =  227
        assert c.s_ushort               ==  227
        cppyy_test_data.s_int            = -234
        assert c.s_int                  == -234
        c.s_int                          = -321
        assert cppyy_test_data.s_int    == -321
        cppyy_test_data.s_uint           = 1234
        assert c.s_uint                 == 1234
        c.s_uint                         = 4321
        assert cppyy_test_data.s_uint   == 4321
        raises(ValueError, setattr, c,               's_uint', -1)
        raises(ValueError, setattr, cppyy_test_data, 's_uint', -1)
        cppyy_test_data.s_long           = -87L
        assert c.s_long                 == -87L
        c.s_long                         = 876L
        assert cppyy_test_data.s_long   == 876L
        cppyy_test_data.s_ulong          = 876L
        assert c.s_ulong                == 876L
        c.s_ulong                        = 678L
        assert cppyy_test_data.s_ulong  == 678L
        raises(ValueError, setattr, cppyy_test_data, 's_ulong', -1)
        raises(ValueError, setattr, c,               's_ulong', -1)

        # floating point types
        cppyy_test_data.s_float                    = -3.1415
        assert round(c.s_float, 5 )               == -3.1415
        c.s_float                                  =  3.1415
        assert round(cppyy_test_data.s_float, 5 ) ==  3.1415
        import math
        c.s_double                                 = -math.pi
        assert cppyy_test_data.s_double           == -math.pi
        cppyy_test_data.s_double                   =  math.pi
        assert c.s_double                         ==  math.pi

        c.destruct()

    def test5_range_access(self):
        """Test the ranges of integer types"""

        import cppyy, sys
        cppyy_test_data = cppyy.gbl.cppyy_test_data

        c = cppyy_test_data()
        assert isinstance(c, cppyy_test_data)

        # TODO: should these be TypeErrors, or should char/bool raise
        #       ValueErrors? In any case, consistency is needed ...
        raises(ValueError, setattr, c, 'm_uint',  -1)
        raises(ValueError, setattr, c, 'm_ulong', -1)

        c.destruct()

    def test6_type_conversions(self):
        """Test conversions between builtin types"""

        import cppyy, sys
        cppyy_test_data = cppyy.gbl.cppyy_test_data

        c = cppyy_test_data()
        assert isinstance(c, cppyy_test_data)

        c.m_double = -1
        assert round(c.m_double + 1.0, 8) == 0

        raises(TypeError, c.m_double,  'c')
        raises(TypeError, c.m_int,     -1.)
        raises(TypeError, c.m_int,      1.)

        c.destruct()
