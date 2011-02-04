import py, os, sys
from pypy.conftest import gettestobjspace
from pypy.module.cppyy import interp_cppyy, executor


currpath = py.path.local(__file__).dirpath()
shared_lib = str(currpath.join("datatypesDict.so"))

space = gettestobjspace(usemodules=['cppyy'])

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

    def testLoadLibCache(self):
        """Test whether loading a library twice results in the same object."""
        import cppyy
        lib2 = cppyy.load_lib(self.shared_lib)
        assert self.datatypes is lib2

    def test1ReadAccess( self ):
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
            """
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
            """

        """
        # out-of-bounds checks
        raises(IndexError, c.m_short_array.__getitem__,  self.N)
        raises(IndexError, c.m_ushort_array.__getitem__, self.N)
        raises(IndexError, c.m_int_array.__getitem__,    self.N)
        raises(IndexError, c.m_uint_array.__getitem__,   self.N)
        raises(IndexError, c.m_long_array.__getitem__,   self.N)
        raises(IndexError, c.m_ulong_array.__getitem__,  self.N)
        raises(IndexError, c.m_float_array.__getitem__,  self.N)
        raises(IndexError, c.m_double_array.__getitem__, self.N)
        """

        c.destruct()

    def test2WriteAccess(self):
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

# TODO: be able to dissect array.array for its pointers
#            exec 'c.m_%s_array2 = b' % names[j]  # pointer copies
#            b[i] = 28
#            for i in range(self.N):
#                assert eval('c.m_%s_array2[i]' % names[j]) == b[i]

        c.destruct()

    def test3RangeAccess(self):
        """Test the ranges of integer types"""

        import cppyy, sys
        cppyy_test_data = cppyy.gbl.cppyy_test_data

        c = cppyy_test_data()
        assert isinstance(c, cppyy_test_data)

        raises(ValueError, setattr, c, 'm_uint',  -1)
        raises(ValueError, setattr, c, 'm_ulong', -1)

        c.destruct()

    def test4TypeConversions(self):
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
