import py, os, sys


currpath = py.path.local(__file__).dirpath()
test_dct = str(currpath.join("datatypesDict.so"))

def setup_module(mod):
    if sys.platform == 'win32':
        py.test.skip("win32 not supported so far")
    err = os.system("cd '%s' && make datatypesDict.so" % currpath)
    if err:
        raise OSError("'make' failed (see stderr)")

class AppTestDATATYPES:
    spaceconfig = dict(usemodules=['cppyy', '_rawffi', 'itertools'])

    def setup_class(cls):
        cls.w_N = cls.space.newint(5)  # should be imported from the dictionary
        cls.w_test_dct  = cls.space.newtext(test_dct)
        cls.w_datatypes = cls.space.appexec([], """():
            import cppyy
            return cppyy.load_reflection_info(%r)""" % (test_dct, ))

    def test01_load_reflection_cache(self):
        """Test whether loading a refl. info twice results in the same object."""
        import cppyy
        lib2 = cppyy.load_reflection_info(self.test_dct)
        assert self.datatypes is lib2

    def test02_instance_data_read_access(self):
        """Test read access to instance public data and verify values"""

        import cppyy
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
        assert c.m_llong  == -44
        assert c.m_ullong ==  55

        # reading floating point types
        assert round(c.m_float  + 66., 5) == 0
        assert round(c.m_double + 77., 8) == 0

        # reding of array types
        for i in range(self.N):
            # reading of integer array types
            assert c.m_bool_array[i]        ==   bool(i%2)
            assert c.get_bool_array()[i]    ==   bool(i%2)
            assert c.m_bool_array2[i]       ==   bool((i+1)%2)
            assert c.get_bool_array2()[i]   ==   bool((i+1)%2)
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

        # can not access an instance member on the class
        raises(ReferenceError, getattr, cppyy_test_data, 'm_bool')
        raises(ReferenceError, getattr, cppyy_test_data, 'm_int')

        assert not hasattr(cppyy_test_data, 'm_bool')
        assert not hasattr(cppyy_test_data, 'm_int')

        c.destruct()

    def test03_instance_data_write_access(self):
        """Test write access to instance public data and verify values"""

        import cppyy
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

        raises(ValueError, 'c.set_bool(10)')

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

        raises(ValueError, 'c.set_char("string")')
        raises(ValueError, 'c.set_char(500)')
        raises(ValueError, 'c.set_uchar("string")')
        raises(ValueError, 'c.set_uchar(-1)')

        # integer types
        names = ['short', 'ushort', 'int', 'uint', 'long', 'ulong', 'llong', 'ullong']
        for i in range(len(names)):
            exec 'c.m_%s = %d' % (names[i],i)
            assert eval('c.get_%s()' % names[i]) == i

        for i in range(len(names)):
            exec 'c.set_%s(%d)' % (names[i],2*i)
            assert eval('c.m_%s' % names[i]) == 2*i

        for i in range(len(names)):
            exec 'c.set_%s_c(%d)' % (names[i],3*i)
            assert eval('c.m_%s' % names[i]) == 3*i

        # float types through functions
        c.set_float( 0.123 );  assert round(c.get_float()  - 0.123, 5) == 0
        c.set_double( 0.456 ); assert round(c.get_double() - 0.456, 8) == 0

        # float types through data members
        c.m_float = 0.123;     assert round(c.get_float()  - 0.123, 5) == 0
        c.set_float(0.234);    assert round(c.m_float      - 0.234, 5) == 0
        c.set_float_c(0.456);  assert round(c.m_float      - 0.456, 5) == 0
        c.m_double = 0.678;    assert round(c.get_double() - 0.678, 8) == 0
        c.set_double(0.890);   assert round(c.m_double     - 0.890, 8) == 0
        c.set_double_c(0.012); assert round(c.m_double     - 0.012, 8) == 0

        # arrays; there will be pointer copies, so destroy the current ones
        c.destroy_arrays()

        # integer arrays
        names = ['short', 'ushort', 'int', 'uint', 'long', 'ulong']
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

    def test04_array_passing(self):
        """Test passing of array arguments"""

        import cppyy, array, sys
        cppyy_test_data = cppyy.gbl.cppyy_test_data

        c = cppyy_test_data()
        assert isinstance(c, cppyy_test_data)

        a = range(self.N)
        # test arrays in mixed order, to give overload resolution a workout
        for t in ['d', 'i', 'f', 'H', 'I', 'h', 'L', 'l' ]:
            b = array.array(t, a)

            # typed passing
            ca = c.pass_array(b)
            assert type(ca[0]) == type(b[0])
            assert len(b) == self.N
            for i in range(self.N):
                assert ca[i] == b[i]

            # void* passing
            ca = eval('c.pass_void_array_%s(b)' % t)
            assert type(ca[0]) == type(b[0])
            assert len(b) == self.N
            for i in range(self.N):
                assert ca[i] == b[i]

        # NULL/None/nullptr passing (will use short*)
        assert not c.pass_array(0)
        raises(Exception, c.pass_array(0).__getitem__, 0)    # raises SegfaultException
        assert not c.pass_array(None)
        raises(Exception, c.pass_array(None).__getitem__, 0) # id.
        assert not c.pass_array(cppyy.gbl.nullptr)
        raises(Exception, c.pass_array(cppyy.gbl.nullptr).__getitem__, 0) # id. id.

        c.destruct()

    def test05_class_read_access(self):
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
        assert cppyy_test_data.s_llong  == -404L
        assert c.s_llong                == -404L
        assert c.s_ullong               ==  505L
        assert cppyy_test_data.s_ullong ==  505L

        # floating point types
        assert round(cppyy_test_data.s_float  + 606., 5) == 0
        assert round(c.s_float                + 606., 5) == 0
        assert round(cppyy_test_data.s_double + 707., 8) == 0
        assert round(c.s_double               + 707., 8) == 0

        c.destruct()

    def test06_class_data_write_access(self):
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
        raises(ValueError, setattr, cppyy_test_data, 's_uchar', -1)
        raises(ValueError, setattr, c,               's_uchar', -1)

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

    def test07_range_access(self):
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

    def test08_type_conversions(self):
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

    def test09_global_builtin_type(self):
        """Test access to a global builtin type"""

        import cppyy
        gbl = cppyy.gbl

        assert gbl.g_int == gbl.get_global_int()

        gbl.set_global_int(32)
        assert gbl.get_global_int() == 32
        assert gbl.g_int == 32

        gbl.g_int = 22
        assert gbl.get_global_int() == 22
        assert gbl.g_int == 22

    def test10_global_ptr(self):
        """Test access of global objects through a pointer"""

        import cppyy
        gbl = cppyy.gbl

        raises(ReferenceError, 'gbl.g_pod.m_int')

        c = gbl.cppyy_test_pod()
        c.m_int = 42
        c.m_double = 3.14

        gbl.set_global_pod(c)
        assert gbl.is_global_pod(c)
        assert gbl.g_pod.m_int == 42
        assert gbl.g_pod.m_double == 3.14

        d = gbl.get_global_pod()
        assert gbl.is_global_pod(d)
        assert c == d
        assert id(c) == id(d)

        e = gbl.cppyy_test_pod()
        e.m_int = 43
        e.m_double = 2.14

        gbl.g_pod = e
        assert gbl.is_global_pod(e)
        assert gbl.g_pod.m_int == 43
        assert gbl.g_pod.m_double == 2.14

    def test11_enum(self):
        """Test access to enums"""

        import cppyy
        gbl = cppyy.gbl

        cppyy_test_data = cppyy.gbl.cppyy_test_data

        c = cppyy_test_data()
        assert isinstance(c, cppyy_test_data)

        # test that the enum is accessible as a type
        assert cppyy_test_data.what

        assert cppyy_test_data.kNothing   ==   6
        assert cppyy_test_data.kSomething == 111
        assert cppyy_test_data.kLots      ==  42

        assert cppyy_test_data.what(cppyy_test_data.kNothing) == cppyy_test_data.kNothing
        assert cppyy_test_data.what(6) == cppyy_test_data.kNothing
        # TODO: only allow instantiations with correct values (C++11)

        assert c.get_enum() == cppyy_test_data.kNothing
        assert c.m_enum == cppyy_test_data.kNothing

        c.m_enum = cppyy_test_data.kSomething
        assert c.get_enum() == cppyy_test_data.kSomething
        assert c.m_enum == cppyy_test_data.kSomething

        c.set_enum(cppyy_test_data.kLots)
        assert c.get_enum() == cppyy_test_data.kLots
        assert c.m_enum == cppyy_test_data.kLots

        assert c.s_enum == cppyy_test_data.s_enum
        assert c.s_enum == cppyy_test_data.kNothing
        assert cppyy_test_data.s_enum == cppyy_test_data.kNothing

        c.s_enum = cppyy_test_data.kSomething
        assert c.s_enum == cppyy_test_data.s_enum
        assert c.s_enum == cppyy_test_data.kSomething
        assert cppyy_test_data.s_enum == cppyy_test_data.kSomething

        # global enums
        assert gbl.fruit          # test type accessible
        assert gbl.kApple  == 78
        assert gbl.kBanana == 29
        assert gbl.kCitrus == 34

    def test12_string_passing(self):
        """Test passing/returning of a const char*"""

        import cppyy
        cppyy_test_data = cppyy.gbl.cppyy_test_data

        c = cppyy_test_data()
        assert c.get_valid_string('aap') == 'aap'
        #assert c.get_invalid_string() == ''

    def test13_copy_contructor(self):
        """Test copy constructor"""

        import cppyy
        four_vector = cppyy.gbl.four_vector

        t1 = four_vector(1., 2., 3., -4.)
        t2 = four_vector(0., 0., 0.,  0.)
        t3 = four_vector(t1)

        assert t1 == t3
        assert t1 != t2

        for i in range(4):
            assert t1[i] == t3[i]

    def test14_object_returns(self):
        """Test access to and return of PODs"""

        import cppyy

        c = cppyy.gbl.cppyy_test_data()

        assert c.m_pod.m_int == 888
        assert c.m_pod.m_double == 3.14

        pod = c.get_pod_val()
        assert pod.m_int == 888
        assert pod.m_double == 3.14

        assert c.get_pod_val_ptr().m_int == 888
        assert c.get_pod_val_ptr().m_double == 3.14
        c.get_pod_val_ptr().m_int = 777
        assert c.get_pod_val_ptr().m_int == 777

        assert c.get_pod_val_ref().m_int == 777
        assert c.get_pod_val_ref().m_double == 3.14
        c.get_pod_val_ref().m_int = 666
        assert c.get_pod_val_ref().m_int == 666

        assert c.get_pod_ptrref().m_int == 666
        assert c.get_pod_ptrref().m_double == 3.14

    def test15_object_arguments(self):
        """Test setting and returning of a POD through arguments"""

        import cppyy

        c = cppyy.gbl.cppyy_test_data()
        assert c.m_pod.m_int == 888
        assert c.m_pod.m_double == 3.14

        p = cppyy.gbl.cppyy_test_pod()
        p.m_int = 123
        assert p.m_int == 123
        p.m_double = 321.
        assert p.m_double == 321.

        c.set_pod_val(p)
        assert c.m_pod.m_int == 123
        assert c.m_pod.m_double == 321.

        c = cppyy.gbl.cppyy_test_data()
        c.set_pod_ptr_in(p)
        assert c.m_pod.m_int == 123
        assert c.m_pod.m_double == 321.

        c = cppyy.gbl.cppyy_test_data()
        c.set_pod_ptr_out(p)
        assert p.m_int == 888
        assert p.m_double == 3.14

        p.m_int = 555
        p.m_double = 666.

        c = cppyy.gbl.cppyy_test_data()
        c.set_pod_ref(p)
        assert c.m_pod.m_int == 555
        assert c.m_pod.m_double == 666.

        c = cppyy.gbl.cppyy_test_data()
        c.set_pod_ptrptr_in(p)
        assert c.m_pod.m_int == 555
        assert c.m_pod.m_double == 666.
        assert p.m_int == 555
        assert p.m_double == 666.

        c = cppyy.gbl.cppyy_test_data()
        c.set_pod_void_ptrptr_in(p)
        assert c.m_pod.m_int == 555
        assert c.m_pod.m_double == 666.
        assert p.m_int == 555
        assert p.m_double == 666.

        c = cppyy.gbl.cppyy_test_data()
        c.set_pod_ptrptr_out(p)
        assert c.m_pod.m_int == 888
        assert c.m_pod.m_double == 3.14
        assert p.m_int == 888
        assert p.m_double == 3.14

        p.m_int = 777
        p.m_double = 888.

        c = cppyy.gbl.cppyy_test_data()
        c.set_pod_void_ptrptr_out(p)
        assert c.m_pod.m_int == 888
        assert c.m_pod.m_double == 3.14
        assert p.m_int == 888
        assert p.m_double == 3.14

    def test16_nullptr_passing(self):
        """Integer 0 ('NULL') and None allowed to pass through instance*"""

        import cppyy

        for o in (0, None):
            c = cppyy.gbl.cppyy_test_data()
            assert c.m_pod.m_int == 888
            assert c.m_pod.m_double == 3.14
            assert not not c.m_ppod

            c.set_pod_ptr(o)
            assert not c.m_ppod
            assert not c.get_pod_ptr()

    def test17_respect_privacy(self):
        """Test that privacy settings are respected"""

        import cppyy
        cppyy_test_data = cppyy.gbl.cppyy_test_data

        c = cppyy_test_data()
        assert isinstance(c, cppyy_test_data)

        raises(AttributeError, getattr, c, 'm_owns_arrays')

        c.destruct()

    def test18_object_and_pointer_comparisons(self):
        """Verify object and pointer comparisons"""

        import cppyy
        gbl = cppyy.gbl

        c1 = cppyy.bind_object(0, gbl.cppyy_test_data)
        assert c1 == None
        assert None == c1

        c2 = cppyy.bind_object(0, gbl.cppyy_test_data)
        assert c1 == c2
        assert c2 == c1

        # four_vector overrides operator==
        l1 = cppyy.bind_object(0, gbl.four_vector)
        assert l1 == None
        assert None == l1

        assert c1 != l1
        assert l1 != c1

        l2 = cppyy.bind_object(0, gbl.four_vector)
        assert l1 == l2
        assert l2 == l1

        l3 = gbl.four_vector(1, 2, 3, 4)
        l4 = gbl.four_vector(1, 2, 3, 4)
        l5 = gbl.four_vector(4, 3, 2, 1)
        assert l3 == l4
        assert l4 == l3

        assert l3 != None                 # like this to ensure __ne__ is called
        assert None != l3                 # id.
        assert l3 != l5
        assert l5 != l3

    def test19_object_validity(self):
        """Test object validity checking"""

        from cppyy import gbl

        d = gbl.cppyy_test_pod()

        assert d
        assert not not d

        d2 = gbl.get_null_pod()

        assert not d2

    def test20_buffer_reshaping(self):
        """Test usage of buffer sizing"""

        import cppyy
        cppyy_test_data = cppyy.gbl.cppyy_test_data

        c = cppyy_test_data()
        for func in ['get_bool_array',   'get_bool_array2',
                     'get_ushort_array', 'get_ushort_array2',
                     'get_int_array',    'get_int_array2',
                     'get_uint_array',   'get_uint_array2',
                     'get_long_array',   'get_long_array2',
                     'get_ulong_array',  'get_ulong_array2']:
            arr = getattr(c, func)()
            arr = arr.shape.fromaddress(arr.itemaddress(0), self.N)
            assert len(arr) == self.N

            l = list(arr)
            for i in range(self.N):
                assert arr[i] == l[i]

    def test21_voidp(self):
        """Test usage of void* data"""

        import cppyy
        cppyy_test_data = cppyy.gbl.cppyy_test_data

        c = cppyy_test_data()

        assert not cppyy.gbl.nullptr

        assert c.s_voidp                is cppyy.gbl.nullptr
        assert cppyy_test_data.s_voidp  is cppyy.gbl.nullptr

        assert c.m_voidp                is cppyy.gbl.nullptr
        assert c.get_voidp()            is cppyy.gbl.nullptr

        c2 = cppyy_test_data()
        assert c2.m_voidp               is cppyy.gbl.nullptr
        c.set_voidp(c2.m_voidp)
        assert c.m_voidp                is cppyy.gbl.nullptr
        c.set_voidp(c2.get_voidp())
        assert c.m_voidp                is cppyy.gbl.nullptr
        c.set_voidp(cppyy.gbl.nullptr)
        assert c.m_voidp                is cppyy.gbl.nullptr

        c.set_voidp(c2)
        def address_equality_test(a, b):
            assert cppyy.addressof(a) == cppyy.addressof(b)
            b2 = cppyy.bind_object(a, cppyy_test_data)
            assert b is b2    # memory regulator recycles
            b3 = cppyy.bind_object(cppyy.addressof(a), cppyy_test_data)
            assert b is b3    # likewise

        address_equality_test(c.m_voidp, c2)
        address_equality_test(c.get_voidp(), c2)

        def null_test(null):
            c.m_voidp = null
            assert c.m_voidp is cppyy.gbl.nullptr
        map(null_test, [0, None, cppyy.gbl.nullptr])

        c.m_voidp = c2
        address_equality_test(c.m_voidp,     c2)
        address_equality_test(c.get_voidp(), c2)

        c.s_voidp = c2
        address_equality_test(c.s_voidp, c2)
