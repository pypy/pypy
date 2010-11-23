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

    def test2WriteAccess( self ):
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

#            exec 'c.m_%s_array2 = b' % names[j]  # pointer copies
#            b[i] = 28
#            for i in range(self.N):
#                assert eval('c.m_%s_array2[i]' % names[j]) == b[i]

        c.destruct()
