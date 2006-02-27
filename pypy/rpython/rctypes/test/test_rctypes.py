"""
Test the rctypes implementation.
"""

import py.test
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.translator.translator import TranslationContext
from pypy.translator.c.test.test_genc import compile, compile_db
#o#from pypy.translator.c import compile
from pypy.translator.tool.cbuild import compile_c_module
from pypy.annotation.model import SomeCTypesObject, SomeObject
from pypy import conftest
import sys

thisdir = py.magic.autopath().dirpath()

def compile(fn, argtypes, view=conftest.option.view):
    from pypy.translator.c.database import LowLevelDatabase
    from pypy.rpython.lltypesystem.lltype import pyobjectptr
    t = TranslationContext()
    a = t.buildannotator()
    a.build_types(fn, argtypes)
    t.buildrtyper().specialize()
    if view:
        t.view()
    #t#backend_optimizations(t)
    db = LowLevelDatabase(t)
    entrypoint = db.get(pyobjectptr(fn))
    db.complete()
    module = compile_db(db)
    compiled_fn = getattr(module, entrypoint)
    def checking_fn(*args, **kwds):
        res = compiled_fn(*args, **kwds)
        mallocs, frees = module.malloc_counters()
        assert mallocs == frees
        return res
    return checking_fn
    
try:
    import ctypes
except ImportError:
    py.test.skip("this test needs ctypes installed")


from pypy.rpython.rctypes import cdll, c_char_p, c_int, c_char, \
        c_char, c_byte, c_ubyte, c_short, c_ushort, c_uint,\
        c_long, c_ulong, c_longlong, c_ulonglong, c_float, c_double, \
        POINTER, Structure, byref, ARRAY

# LoadLibrary is deprecated in ctypes, this should be removed at some point
if "load" in dir(cdll):
    cdll_load = cdll.load
else:
    cdll_load = cdll.LoadLibrary

if sys.platform == 'win32':
    mylib = cdll_load('msvcrt.dll')
elif sys.platform == 'linux2':
    mylib = cdll_load('libc.so.6')
elif sys.platform == 'darwin':
    mylib = cdll.c
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
# XXX the built module and intermediate files should go to /tmp/usession-*,
#     see pypy.tool.udir
compile_c_module([thisdir.join("_rctypes_test.c")], "_rctypes_test")

if sys.platform == "win32":
    _rctypes_test = cdll_load("_rctypes_test.pyd")
else:
    _rctypes_test = cdll_load(str(thisdir.join("_rctypes_test.so")))

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


oppoint_type = POINTER(tagpoint)

# _test_struct_id_pointer
testfunc_struct_pointer_id = _rctypes_test._testfunc_struct_pointer_id
testfunc_struct_pointer_id.restype = oppoint_type
testfunc_struct_pointer_id.argtypes = [oppoint_type]

def py_testfunc_struct_pointer_id(inpoint):
    return testfunc_struct_pointer_id(inpoint)


def py_create_point():
    p = tagpoint()
    p.x = 10
    p.y = 20
    return p.x + p.y

def py_testfunc_POINTER(inpoint):
    point = tagpoint()
    oppoint = oppoint_type(point)
    res  = testfunc_byval(inpoint,oppoint)
    return res, oppoint

def py_testfunc_POINTER_dereference(inpoint):
    point = tagpoint()
    oppoint = oppoint_type(point)
    res  = testfunc_byval(inpoint,oppoint)
    return res, oppoint.contents, oppoint[0]

def py_test_mixed_memory_state( randomboolean ):
    if randomboolean:
        return tagpoint()
    else:
        return oppoint_type(tagpoint()).contents

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

c_int_10 = ARRAY(c_int,10)
c_int_p_test = POINTER(c_int)

def py_test_annotate_array():
    return c_int_10()

def py_test_annotate_array_content():
    my_array = c_int_10()
    my_array[0] = c_int(1)
    my_array[1] = 2

    return my_array[0]

def py_test_annotate_pointer_content():
    # Never run this function!
    # See test_annotate_pointer_access_as_array_or_whatever
    # for the weird reasons why this gets annotated
    my_pointer = c_int_p_test(10)
    my_pointer[0] = c_int(1)
    my_pointer[1] = 2

    return my_pointer[0]

def py_test_annotate_array_slice_content():
    my_array = c_int_10()
    #f#my_array[0:7] = c_int(1) * 7
    my_array[0:5] = range(5)

    return my_array[0:5]

def py_test_annotate_array_content_variable_index():
    my_array = c_int_10()
    my_array[2] = 2
    sum = 0
    for idx in range(10):
        sum += my_array[idx]

    return sum

def py_test_annotate_array_content_index_error_on_positive_index():
    my_array = c_int_10()
    return my_array[10]

def py_test_annotate_array_content_index_error_on_negative_index():
    my_array = c_int_10()
    return my_array[-11]

def py_test_specialize_struct():
    p = tagpoint()
    p.x = 1
    p.y = 2
    return p.x

def _py_test_compile_struct( p, x, y ):
    p.x = x
    p.y = y
    return p

def py_test_compile_struct( x, y ):
    return _py_test_compile_struct( tagpoint(), x, y ).x
    
def py_test_compile_pointer( x, y ):
    return _py_test_compile_pointer( oppoint_type( tagpoint() ), x, y ).x

def _py_test_compile_pointer( p, x, y ):
    s = p.contents
    s.x = x
    s.y = y
    return s


class Test_rctypes:

    def test_simple(self):
        res = o_atoi('42')   
        assert res == 42 

    def test_annotate_simple(self):
        a = RPythonAnnotator()
        s = a.build_types(o_atoi, [str])
        # result should be an integer
        assert s.knowntype == int

    def failing_test_specialize_simple(self):
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(o_atoi, [str])
        # result should be an integer
        assert s.knowntype == int
        t.buildrtyper().specialize()
        #d#t.view()

    def failing_test_compile_simple(self):
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
            dll = cdll_load("_rctypes_test.pyd")
        else:
            dll = cdll_load(str(thisdir.join("_rctypes_test.so")))
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
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(py_testfunc_struct_id, [tagpoint])
        assert s.knowntype == tagpoint
        assert s.memorystate == SomeCTypesObject.OWNSMEMORY

    def test_annotate_pointer_to_struct(self):
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(py_testfunc_struct_pointer_id, [oppoint_type])
        assert s.knowntype == oppoint_type
        assert s.memorystate == SomeCTypesObject.MEMORYALIAS
        return t

    def test_create_point(self):
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(py_create_point,[])
        assert s.knowntype == int

    def test_annotate_byval(self):
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(py_testfunc_byval,[tagpoint])
        assert s.knowntype == tuple
        assert len(s.items) == 2
        assert s.items[0].knowntype == int
        assert s.items[1].knowntype == tagpoint
        assert s.items[1].memorystate == SomeCTypesObject.OWNSMEMORY 

    def test_annotate_POINTER(self):
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(py_testfunc_POINTER,[tagpoint])
        assert s.knowntype == tuple
        assert len(s.items) == 2
        assert s.items[0].knowntype == int
        assert s.items[1].knowntype == POINTER(tagpoint)
        assert s.items[1].memorystate == SomeCTypesObject.OWNSMEMORY 
        #d#t.view()

    def test_annotate_POINTER_dereference(self):
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(py_testfunc_POINTER_dereference, [tagpoint])
        assert s.knowntype == tuple
        assert len(s.items) == 3
        assert s.items[0].knowntype == int
        assert s.items[1].knowntype == tagpoint
        assert s.items[1].memorystate == SomeCTypesObject.OWNSMEMORY 
        assert s.items[2].knowntype == tagpoint
        assert s.items[2].memorystate == SomeCTypesObject.OWNSMEMORY 
        #d#t.view()
    
    def test_annotate_mixed_memorystate(self):
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(py_test_mixed_memory_state, [int])
        #d#t.view()
        assert s.knowntype == tagpoint
        # This memory state will be supported in the future (#f#)
        # Obviously the test is wrong for now
        #f#assert s.memorystate == SomeCTypesObject.MIXEDMEMORYOWNERSHIP
        assert isinstance(s, SomeObject)

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

    def test_specialize_struct(self):
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(py_test_specialize_struct, [])
        # result should be an integer
        assert s.knowntype == int
        try:
            t.buildrtyper().specialize()
        finally:
            #d#t.view()
            pass

    def test_specialize_struct_1(self):
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(py_test_compile_struct, [int, int]) 
        #d#t.view()
        try:
            t.buildrtyper().specialize()
        finally:
            #d#t.view()
            pass

    def failing_test_specialize_pointer_to_struct(self):
        t = self.test_annotate_pointer_to_struct()
        t.buildrtyper().specialize()
        #d#t.view()

    def x_test_compile_pointer_to_struct(self):
        fn = compile( py_testfunc_struct_pointer_id, [ oppoint_type ] )

    def test_compile_struct(self):
        fn = compile( py_test_compile_struct, [ int, int ] )
        res = fn( 42, -42 )
        assert res == 42

    def failing_test_specialize_POINTER_dereference(self):
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(py_testfunc_POINTER_dereference, [tagpoint])
        assert s.knowntype == tuple
        try:
            t.buildrtyper().specialize()
        finally:
            #d#t.view()
            pass

    def test_specialize_pointer(self):
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types( py_test_compile_pointer, [ int, int ] )
        assert s.knowntype == int
        #d#t.view()
        t.buildrtyper().specialize()
        #d#t.view()

    def test_compile_pointer(self):
        fn = compile( py_test_compile_pointer, [ int, int ] )
        res = fn( -42, 42 )
        assert res == -42


class Test_array:

    def test_annotate_array(self):
        a = RPythonAnnotator()
        s = a.build_types(py_test_annotate_array, [])
        assert s.knowntype == c_int_10

    def test_annotate_array_access(self):
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(py_test_annotate_array_content, [])
        assert s.knowntype == int
        #d#t.view()

    def test_annotate_pointer_access_as_array(self):
        """
        Make sure that pointers work the same way as arrays, for 
        ctypes compatibility.

        :Note: This works because pointer and array classes both
        have a _type_ attribute, that contains the type of the 
        object pointed to or in the case of an array the element type. 
        """
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(py_test_annotate_pointer_content, [])
        assert s.knowntype == int
        #d#t.view()

    def test_annotate_array_slice_access(self):
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(py_test_annotate_array_slice_content, [])
        #d#t.view()
        #d#print "v90:", s, type(s)
        assert s.knowntype == list
        s.listdef.listitem.s_value.knowntype == int

    def test_annotate_array_access_variable(self):
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(py_test_annotate_array_content_variable_index, [])
        assert s.knowntype == int
        #t#t.view()

    def test_annotate_array_access_index_error_on_positive_index(self):
        t = TranslationContext()
        a = t.buildannotator()
        
        py.test.raises(IndexError, "s = a.build_types(py_test_annotate_array_content_index_error_on_positive_index,[])")

    def test_annotate_array_access_index_error_on_negative_index(self):
        t = TranslationContext()
        a = t.buildannotator()
        
        py.test.raises(IndexError, "s = a.build_types(py_test_annotate_array_content_index_error_on_negative_index,[])")

