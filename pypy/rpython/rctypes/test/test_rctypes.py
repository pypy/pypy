import py.test
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.translator.translator import TranslationContext
from pypy.translator.c.test.test_genc import compile
from pypy.translator.tool.cbuild import compile_c_module
import sys
    
try:
    import ctypes
except ImportError:
    py.test.skip("this test needs ctypes installed")


from pypy.rpython.rctypes import cdll, c_char_p, c_int, c_char, \
        c_char, c_byte, c_ubyte, c_short, c_ushort, c_uint,\
        c_long, c_ulong, c_longlong, c_ulonglong, c_float, c_double, \
        POINTER, Structure, byref
if sys.platform == 'win32':
    mylib = cdll.LoadLibrary('msvcrt.dll')
elif sys.platform == 'linux2':
    mylib = cdll.LoadLibrary('libc.so.6')
else:
    py.test.skip("don't know how to load the c lib for %s" % 
            sys.platform)
atoi = mylib.atoi
atoi.restype = c_int
atoi.argtypes = [c_char_p]
atoi.argtypes = [POINTER(c_char)]

def o_atoi(a):
   return atoi(a)

class tagpoint(Structure):
    _fields_ = [("x", c_int),
                ("y", c_int)]
# compile and load our local test C file
compile_c_module([py.path.local("_rctypes_test.c")], "_rctypes_test")

if sys.platform == "win32":
    _rctypes_test = cdll.LoadLibrary("_rctypes_test.pyd")
else:
    _rctypes_test = cdll.LoadLibrary("_rctypes_test.so")

# _testfunc_byval
testfunc_byval = _rctypes_test._testfunc_byval
testfunc_byval.restype = c_int
testfunc_byval.argtypes = [tagpoint,POINTER(tagpoint)]

def py_testfunc_byval(inpoint):
    opoint = tagpoint()
    res  = testfunc_byval(inpoint,byref(opoint))

    return res, opoint

# _test_struct
testfunc_struct = _rctypes_test._testfunc_struct
testfunc_struct.restype = c_int
testfunc_struct.argtypes = [tagpoint]

def py_testfunc_struct(inpoint):
    return testfunc_struct(inpoint)

# _test_struct_id
testfunc_struct_id = _rctypes_test._testfunc_struct_id
testfunc_struct_id.restype = tagpoint
testfunc_struct_id.argtypes = [tagpoint]

def py_testfunc_struct_id(inpoint):
    return testfunc_struct_id(inpoint)

def py_create_point():
    p = tagpoint()
    p.x = 10
    p.y = 20
    return p.x + p.y

oppoint_type = POINTER(tagpoint)
def py_testfunc_POINTER(inpoint):
    point = tagpoint()
    oppoint = oppoint_type(point)
    res  = testfunc_byval(inpoint,oppoint)
    return res, oppoint

def py_test_simple_cint():
    return c_int(10)

def py_test_simple_ctypes():
    return (
            c_char('a'),
            c_byte(1),
            c_ubyte(1),
            c_short(1),
            c_ushort(1),
            c_int(1),
            c_uint(1),
            c_long(1),
            c_ulong(1),
            c_longlong(1),
            c_ulonglong(1),
            c_float(1.0),
            c_double(1.0)
    )

def py_test_simple_ctypes_non_const():
    a = 10
    return c_float( a + 10 )

class Test_rctypes:

    def test_simple(self):
        res = o_atoi('42')   
        assert res == 42 

    def test_annotate_simple(self):
        a = RPythonAnnotator()
        s = a.build_types(o_atoi, [str])
        # result should be an integer
        assert s.knowntype == int

    def test_specialize_simple(self):
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(o_atoi, [str])
        # result should be an integer
        assert s.knowntype == int
        t.buildrtyper().specialize()
        #d#t.view()

    def test_compile_simple(self):
        fn = compile(o_atoi, [str])
        res = fn("42")
        assert res == 42


class Test_structure:

    def test_simple_as_extension_module(self):
        import _rctypes_test as t0
        import _rctypes_test as t1
        assert t1 is t0
        assert "_rctypes_test" in sys.modules

    def test_simple(self):
        if sys.platform == "win32":
            dll = cdll.LoadLibrary("_rctypes_test.pyd")
        else:
            dll = cdll.LoadLibrary("_rctypes_test.so")
        in_point = tagpoint()
        in_point.x = 42
        in_point.y = 17
        out_point = tagpoint()
        assert in_point.x + in_point.y == dll._testfunc_byval(in_point, byref(out_point))
        assert out_point.x == 42
        assert out_point.y == 17

    def test_structure(self):
        in_point = tagpoint()
        in_point.x = 10
        in_point.y = 20
        res = py_testfunc_struct(in_point)
        assert res == 30

    def test_annotate_struct(self):
        a = RPythonAnnotator()
        s = a.build_types(py_testfunc_struct, [int])
        assert s.knowntype == int


    def test_annotate_struct(self):
        a = RPythonAnnotator()
        s = a.build_types(py_testfunc_struct_id, [tagpoint])
        assert s.knowntype == tagpoint

    def test_create_point(self):
        a = RPythonAnnotator()
        s = a.build_types(py_create_point,[])
        assert s.knowntype == int

    def test_annotate_byval(self):
        a = RPythonAnnotator()
        s = a.build_types(py_testfunc_byval,[tagpoint])
        assert s.knowntype == tuple
        assert len(s.items) == 2
        assert s.items[0].knowntype == int
        assert s.items[1].knowntype == tagpoint

    def test_annotate_POINTER(self):
        a = RPythonAnnotator()
        s = a.build_types(py_testfunc_POINTER,[tagpoint])
        assert s.knowntype == tuple
        assert len(s.items) == 2
        assert s.items[0].knowntype == int
        assert s.items[1].knowntype == POINTER(tagpoint)

    def test_annotate_simple_cint(self):
        a = RPythonAnnotator()
        s = a.build_types(py_test_simple_cint,[])
        assert s.knowntype == c_int

    def test_annotate_simple_types(self):
        a = RPythonAnnotator()
        s = a.build_types(py_test_simple_ctypes,[])
        assert s.knowntype == tuple
        assert len(s.items) == 13
        assert s.items[0].knowntype == c_char
        assert s.items[1].knowntype == c_byte
        assert s.items[2].knowntype == c_ubyte
        assert s.items[3].knowntype == c_short
        assert s.items[4].knowntype == c_ushort
        assert s.items[5].knowntype == c_int
        assert s.items[6].knowntype == c_uint
        assert s.items[7].knowntype == c_long
        assert s.items[8].knowntype == c_ulong
        assert s.items[9].knowntype == c_longlong
        assert s.items[10].knowntype == c_ulonglong
        assert s.items[11].knowntype == c_float
        assert s.items[12].knowntype == c_double

    def test_annotate_simple_types_non_const(self):
        a = RPythonAnnotator()
        s = a.build_types(py_test_simple_ctypes_non_const,[])
        assert s.knowntype == c_float

