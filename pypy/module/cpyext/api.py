import ctypes
import sys
import atexit

import py

from pypy.translator.goal import autopath
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.tool import rffi_platform
from pypy.rpython.lltypesystem import ll2ctypes
from pypy.rpython.annlowlevel import llhelper
from pypy.rlib.objectmodel import we_are_translated
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator.gensupp import NameManager
from pypy.tool.udir import udir
from pypy.tool.sourcetools import func_with_new_name
from pypy.translator import platform
from pypy.interpreter.error import operationerrfmt
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.nestedscope import Cell
from pypy.interpreter.module import Module
from pypy.interpreter.function import StaticMethod
from pypy.interpreter.typedef import TypeDef
from pypy.objspace.std.sliceobject import W_SliceObject
from pypy.module.__builtin__.descriptor import W_Property
from pypy.rlib.entrypoint import entrypoint
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.objectmodel import specialize
from pypy.rlib.exports import export_struct
from pypy.module import exceptions
from pypy.module.exceptions import interp_exceptions
# CPython 2.4 compatibility
from py.builtin import BaseException

DEBUG_WRAPPER = True

# update these for other platforms
Py_ssize_t = lltype.Signed
Py_ssize_tP = rffi.CArrayPtr(Py_ssize_t)
size_t = rffi.ULONG
ADDR = lltype.Signed

pypydir = py.path.local(autopath.pypydir)
include_dir = pypydir / 'module' / 'cpyext' / 'include'
source_dir = pypydir / 'module' / 'cpyext' / 'src'
interfaces_dir = pypydir / "_interfaces"
include_dirs = [
    include_dir,
    udir,
    interfaces_dir,
    ]

class CConfig:
    _compilation_info_ = ExternalCompilationInfo(
        include_dirs=include_dirs,
        includes=['Python.h', 'stdarg.h'],
        compile_extra=['-DPy_BUILD_CORE'],
        )

class CConfig_constants:
    _compilation_info_ = CConfig._compilation_info_

VA_LIST_P = rffi.VOIDP # rffi.COpaquePtr('va_list')
CONST_STRING = lltype.Ptr(lltype.Array(lltype.Char,
                                       hints={'nolength': True}))
CONST_WSTRING = lltype.Ptr(lltype.Array(lltype.UniChar,
                                        hints={'nolength': True}))
assert CONST_STRING is not rffi.CCHARP
assert CONST_WSTRING is not rffi.CWCHARP

# FILE* interface
FILEP = rffi.COpaquePtr('FILE')
fopen = rffi.llexternal('fopen', [CONST_STRING, CONST_STRING], FILEP)
fclose = rffi.llexternal('fclose', [FILEP], rffi.INT)
fwrite = rffi.llexternal('fwrite',
                         [rffi.VOIDP, rffi.SIZE_T, rffi.SIZE_T, FILEP],
                         rffi.SIZE_T)
fread = rffi.llexternal('fread',
                        [rffi.VOIDP, rffi.SIZE_T, rffi.SIZE_T, FILEP],
                        rffi.SIZE_T)
feof = rffi.llexternal('feof', [FILEP], rffi.INT)
if sys.platform == 'win32':
    fileno = rffi.llexternal('_fileno', [FILEP], rffi.INT)
else:
    fileno = rffi.llexternal('fileno', [FILEP], rffi.INT)


constant_names = """
Py_TPFLAGS_READY Py_TPFLAGS_READYING
METH_COEXIST METH_STATIC METH_CLASS 
METH_NOARGS METH_VARARGS METH_KEYWORDS METH_O
Py_TPFLAGS_HEAPTYPE Py_TPFLAGS_HAVE_CLASS
Py_LT Py_LE Py_EQ Py_NE Py_GT Py_GE
""".split()
for name in constant_names:
    setattr(CConfig_constants, name, rffi_platform.ConstantInteger(name))
udir.join('pypy_decl.h').write("/* Will be filled later */")
udir.join('pypy_macros.h').write("/* Will be filled later */")
globals().update(rffi_platform.configure(CConfig_constants))

class BaseApiObject:
    """Base class for all objects defined by the CPython API.  each
    object kind may have a declaration in a header file, a definition,
    and methods to initialize it, to retrive it in test."""

    def get_llpointer(self, space):
        raise NotImplementedError

    def get_interpret(self, space):
        raise NotImplementedError

cpyext_namespace = NameManager('cpyext_')

class ApiFunction(BaseApiObject):
    def __init__(self, argtypes, restype, callable, error, c_name=None):
        self.argtypes = argtypes
        self.restype = restype
        self.functype = lltype.Ptr(lltype.FuncType(argtypes, restype))
        self.callable = callable
        self.error_value = error
        self.c_name = c_name

        # extract the signature from user code object
        from pypy.interpreter import pycode
        argnames, varargname, kwargname = pycode.cpython_code_signature(
            callable.func_code)

        assert argnames[0] == 'space'
        self.argnames = argnames[1:]
        assert len(self.argnames) == len(self.argtypes)

    def _freeze_(self):
        return True

    def get_llpointer(self, space):
        "Returns a C function pointer"
        assert not we_are_translated() # NOT_RPYTHON??
        llh = getattr(self, '_llhelper', None)
        if llh is None:
            llh = llhelper(self.functype, self._get_wrapper(space))
            self._llhelper = llh
        return llh

    @specialize.memo()
    def get_llpointer_maker(self, space):
        "Returns a callable that builds a C function pointer"
        return lambda: llhelper(self.functype, self._get_wrapper(space))

    @specialize.memo()
    def _get_wrapper(self, space):
        wrapper = getattr(self, '_wrapper', None)
        if wrapper is None:
            from pypy.module.cpyext.gateway import make_wrapper
            wrapper = make_wrapper(space, self.callable)
            self._wrapper = wrapper
            wrapper.relax_sig_check = True
            if self.c_name is not None:
                wrapper.c_name = cpyext_namespace.uniquename(self.c_name)
        return wrapper

def FUNCTION_declare(name, api_func):
    assert name not in FUNCTIONS, "%s already registered" % (name,)
    FUNCTIONS[name] = api_func

def INTERPLEVEL_declare(name, obj):
    INTERPLEVEL_API[name] = obj

def copy_header_files():
    for name in ("pypy_decl.h", "pypy_macros.h"):
        udir.join(name).copy(interfaces_dir / name)

def cpython_struct(name, fields, forward=None):
    configname = name.replace(' ', '__')
    setattr(CConfig, configname, rffi_platform.Struct(name, fields))
    if forward is None:
        forward = lltype.ForwardReference()
    TYPES[configname] = forward
    return forward

INTERPLEVEL_API = {}
FUNCTIONS = {}
SYMBOLS_C = []

def gather_PyAPI_symbols():
    import os, re
    include_dir = py.path.local(__file__).dirpath() / 'include'
    for filename in include_dir.listdir("*.h"):
        for line in filename.open():
            if 'PyAPI_' not in line:
                continue
            if re.match('# *define', line):
                continue

            match = re.match(r'PyAPI_FUNC\(.+?\)\s+(.+)\(', line)
            if match:
                name = match.group(1)
                SYMBOLS_C.append(name)
                continue
            match = re.match(r'PyAPI_DATA\(.+?\)\s+(.+);', line)
            if match:
                name = match.group(1)
                SYMBOLS_C.append(name)
                continue

            assert False, "unknown PyAPI declaration: %r" % (line,)
gather_PyAPI_symbols()

TYPES = {}
GLOBALS = {}
FORWARD_DECLS = []
INIT_FUNCTIONS = []
BOOTSTRAP_FUNCTIONS = []

def attach_and_track(space, py_obj, w_obj):
    from pypy.module.cpyext.pyobject import (
        track_reference, get_typedescr, make_ref)
    w_type = space.type(w_obj)
    typedescr = get_typedescr(w_type.instancetypedef)
    py_obj.c_ob_refcnt = 1
    py_obj.c_ob_type = rffi.cast(PyTypeObjectPtr,
                                 make_ref(space, w_type))
    typedescr.attach(space, py_obj, w_obj)
    track_reference(space, py_obj, w_obj)

class BaseGlobalObject:
    """Base class for all objects (pointers and structures)"""

    @classmethod
    def declare(cls, *args, **kwargs):
        obj = cls(*args, **kwargs)
        GLOBALS[obj.name] = obj

    def eval(self, space):
        from pypy.module import cpyext
        return eval(self.expr)

    def get_data_declaration(self):
        type = self.get_type_for_declaration()
        return 'PyAPI_DATA(%s) %s;' % (type, self.name)

    def get_data_definition(self):
        type = self.get_type_for_declaration()
        if not self.needs_hidden_global_structure:
            return ['%s %s;' % (type, self.name)]
        else:
            return ['extern %s _%s;' % (self.type[:-1], self.name),
                    '%s %s = (%s)&_%s;' % (type, self.name, type, self.name)]

    def get_global_code_for_bridge(self):
        if not self.needs_hidden_global_structure:
            return []
        else:
            return ['%s _%s;' % (self.type[:-1], self.name)]

class GlobalStaticPyObject(BaseGlobalObject):
    def __init__(self, name, expr):
        self.name = name
        self.type = 'PyObject*'
        self.expr = expr

    needs_hidden_global_structure = False
    def get_type_for_declaration(self):
        return 'PyObject'

    def get_name_for_structnode(self):
        return self.name
    def get_value_for_structnode(self, space, value):
        from pypy.module.cpyext.pyobject import make_ref
        value = make_ref(space, value)
        return value._obj

    def set_value_in_ctypes_dll(self, space, dll, value):
        # it's a structure, get its adress
        in_dll = ll2ctypes.get_ctypes_type(PyObject.TO).in_dll(dll, self.name)
        py_obj = ll2ctypes.ctypes2lltype(PyObject, ctypes.pointer(in_dll))
        attach_and_track(space, py_obj, value)

class GlobalStructurePointer(BaseGlobalObject):
    def __init__(self, name, type, expr):
        self.name = name
        self.type = type
        self.expr = expr

    needs_hidden_global_structure = True
    def get_type_for_declaration(self):
        return self.type

    def get_name_for_structnode(self):
        return '_' + self.name
    def get_value_for_structnode(self, space, value):
        from pypy.module.cpyext.datetime import PyDateTime_CAPI
        return rffi.cast(lltype.Ptr(PyDateTime_CAPI), value)._obj

    def set_value_in_ctypes_dll(self, space, dll, value):
        ptr = ctypes.c_void_p.in_dll(dll, self.name)
        ptr.value = ctypes.cast(ll2ctypes.lltype2ctypes(value),
                                ctypes.c_void_p).value

class GlobalExceptionPointer(BaseGlobalObject):
    def __init__(self, exc_name):
        self.name = 'PyExc_' + exc_name
        self.type = 'PyTypeObject*'
        self.expr = ('space.gettypeobject(interp_exceptions.W_%s.typedef)'
                     % (exc_name,))

    needs_hidden_global_structure = True
    def get_type_for_declaration(self):
        return 'PyObject*'

    def get_name_for_structnode(self):
        return '_' + self.name
    def get_value_for_structnode(self, space, value):
        from pypy.module.cpyext.pyobject import make_ref
        from pypy.module.cpyext.typeobjectdefs import PyTypeObjectPtr
        return rffi.cast(PyTypeObjectPtr, make_ref(space, value))._obj

    def set_value_in_ctypes_dll(self, space, dll, value):
        # it's a pointer
        in_dll = ll2ctypes.get_ctypes_type(PyObject).in_dll(dll, self.name)
        py_obj = ll2ctypes.ctypes2lltype(PyObject, in_dll)
        attach_and_track(space, py_obj, value)

class GlobalTypeObject(BaseGlobalObject):
    def __init__(self, name, expr):
        self.name = 'Py%s_Type' % (name,)
        self.type = 'PyTypeObject*'
        self.expr = expr

    def eval(self, space):
        if isinstance(self.expr, str):
            return BaseGlobalObject.eval(self, space)
        elif isinstance(self.expr, TypeDef):
            return space.gettypeobject(self.expr)
        else:
            raise ValueError, "Unknonwn expression: %r" % (self.expr)

    needs_hidden_global_structure = False
    def get_type_for_declaration(self):
        return 'PyTypeObject'

    def get_name_for_structnode(self):
        return self.name
    def get_value_for_structnode(self, space, value):
        from pypy.module.cpyext.pyobject import make_ref
        from pypy.module.cpyext.typeobjectdefs import PyTypeObjectPtr
        return rffi.cast(PyTypeObjectPtr, make_ref(space, value))._obj

    def set_value_in_ctypes_dll(self, space, dll, value):
        # it's a structure, get its adress
        in_dll = ll2ctypes.get_ctypes_type(PyObject.TO).in_dll(dll, self.name)
        py_obj = ll2ctypes.ctypes2lltype(PyObject, ctypes.pointer(in_dll))
        attach_and_track(space, py_obj, value)

def build_exported_objects():
    # Standard exceptions
    for exc_name in exceptions.Module.interpleveldefs.keys():
        GlobalExceptionPointer.declare(exc_name)

    # Global object structures
    GlobalStaticPyObject.declare('_Py_NoneStruct', 'space.w_None')
    GlobalStaticPyObject.declare('_Py_TrueStruct', 'space.w_True')
    GlobalStaticPyObject.declare('_Py_ZeroStruct', 'space.w_False')
    GlobalStaticPyObject.declare('_Py_EllipsisObject', 'space.w_Ellipsis')
    GlobalStaticPyObject.declare('_Py_NotImplementedStruct',
                                 'space.w_NotImplemented')

    GlobalStructurePointer.declare('PyDateTimeAPI', 'PyDateTime_CAPI*',
                                   'cpyext.datetime.build_datetime_api(space)')

    # Common types with their own struct
    GlobalTypeObject.declare("Type", "space.w_type")
    GlobalTypeObject.declare("String", "space.w_str")
    GlobalTypeObject.declare("Unicode", "space.w_unicode")
    GlobalTypeObject.declare("BaseString", "space.w_basestring")
    GlobalTypeObject.declare("Dict", "space.w_dict")
    GlobalTypeObject.declare("Tuple", "space.w_tuple")
    GlobalTypeObject.declare("List", "space.w_list")
    GlobalTypeObject.declare("Int", "space.w_int")
    GlobalTypeObject.declare("Bool", "space.w_bool")
    GlobalTypeObject.declare("Float", "space.w_float")
    GlobalTypeObject.declare("Long", "space.w_long")
    GlobalTypeObject.declare("Complex", "space.w_complex")
    GlobalTypeObject.declare("BaseObject", "space.w_object")
    GlobalTypeObject.declare("None", "space.type(space.w_None)")
    GlobalTypeObject.declare("NotImplemented", "space.type(space.w_NotImplemented)")
    GlobalTypeObject.declare("Cell", Cell.typedef)
    GlobalTypeObject.declare("Module", Module.typedef)
    GlobalTypeObject.declare("Property", W_Property.typedef)
    GlobalTypeObject.declare("Slice", W_SliceObject.typedef)
    GlobalTypeObject.declare("StaticMethod", StaticMethod.typedef)
    from pypy.module.cpyext.methodobject import W_PyCFunctionObject
    GlobalTypeObject.declare("CFunction", W_PyCFunctionObject.typedef)

    for cpyname in 'Method List Int Long Dict Tuple Class'.split():
        FORWARD_DECLS.append('typedef struct { PyObject_HEAD } '
                             'Py%sObject' % (cpyname, ))

PyTypeObject = lltype.ForwardReference()
PyTypeObjectPtr = lltype.Ptr(PyTypeObject)
# It is important that these PyObjects are allocated in a raw fashion
# Thus we cannot save a forward pointer to the wrapped object
# So we need a forward and backward mapping in our State instance
PyObjectStruct = lltype.ForwardReference()
PyObject = lltype.Ptr(PyObjectStruct)
PyBufferProcs = lltype.ForwardReference()
PyObjectFields = (("ob_refcnt", lltype.Signed), ("ob_type", PyTypeObjectPtr))
def F(ARGS, RESULT=lltype.Signed):
    return lltype.Ptr(lltype.FuncType(ARGS, RESULT))
PyBufferProcsFields = (
    ("bf_getreadbuffer", F([PyObject, lltype.Signed, rffi.VOIDPP])),
    ("bf_getwritebuffer", F([PyObject, lltype.Signed, rffi.VOIDPP])),
    ("bf_getsegcount", F([PyObject, rffi.INTP])),
    ("bf_getcharbuffer", F([PyObject, lltype.Signed, rffi.CCHARPP])),
# we don't support new buffer interface for now
    ("bf_getbuffer", rffi.VOIDP),
    ("bf_releasebuffer", rffi.VOIDP))
PyVarObjectFields = PyObjectFields + (("ob_size", Py_ssize_t), )
cpython_struct('PyObject', PyObjectFields, PyObjectStruct)
cpython_struct('PyBufferProcs', PyBufferProcsFields, PyBufferProcs)
PyVarObjectStruct = cpython_struct("PyVarObject", PyVarObjectFields)
PyVarObject = lltype.Ptr(PyVarObjectStruct)
PyObjectP = rffi.CArrayPtr(PyObject)

def configure_types():
    for name, TYPE in rffi_platform.configure(CConfig).iteritems():
        if name in TYPES:
            TYPES[name].become(TYPE)


def build_type_checkers(type_name, cls=None):
    """
    Builds two api functions: Py_XxxCheck() and Py_XxxCheckExact().
    - if `cls` is None, the type is space.w_[type].
    - if `cls` is a string, it is the name of a space attribute, e.g. 'w_str'.
    - else `cls` must be a W_Class with a typedef.
    """
    if cls is None:
        attrname = "w_" + type_name.lower()
        def get_w_type(space):
            return getattr(space, attrname)
    elif isinstance(cls, str):
        def get_w_type(space):
            return getattr(space, cls)
    else:
        def get_w_type(space):
            return space.gettypeobject(cls.typedef)
    check_name = "Py" + type_name + "_Check"

    def check(space, w_obj):
        "Implements the Py_Xxx_Check function"
        w_obj_type = space.type(w_obj)
        w_type = get_w_type(space)
        return (space.is_w(w_obj_type, w_type) or
                space.is_true(space.issubtype(w_obj_type, w_type)))
    def check_exact(space, w_obj):
        "Implements the Py_Xxx_CheckExact function"
        w_obj_type = space.type(w_obj)
        w_type = get_w_type(space)
        return space.is_w(w_obj_type, w_type)

    from pypy.module.cpyext.gateway import cpython_api, CANNOT_FAIL
    check = cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)(
        func_with_new_name(check, check_name))
    check_exact = cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)(
        func_with_new_name(check_exact, check_name + "Exact"))
    return check, check_exact

def setup_init_functions(eci):
    init_buffer = rffi.llexternal('init_bufferobject', [], lltype.Void, compilation_info=eci)
    init_pycobject = rffi.llexternal('init_pycobject', [], lltype.Void, compilation_info=eci)
    INIT_FUNCTIONS.extend([
        lambda space: init_buffer(),
        lambda space: init_pycobject(),
    ])

def init_function(func):
    INIT_FUNCTIONS.append(func)
    return func

def bootstrap_function(func):
    BOOTSTRAP_FUNCTIONS.append(func)
    return func

def run_bootstrap_functions(space):
    for func in BOOTSTRAP_FUNCTIONS:
        func(space)

def c_function_signature(db, func):
    restype = db.gettype(func.restype).replace('@', '').strip()
    args = []
    for i, argtype in enumerate(func.argtypes):
        if argtype is CONST_STRING:
            arg = 'const char *@'
        elif argtype is CONST_WSTRING:
            arg = 'const wchar_t *@'
        else:
            arg = db.gettype(argtype)
        arg = arg.replace('@', 'arg%d' % (i,)).strip()
        args.append(arg)
    args = ', '.join(args) or "void"
    return restype, args

#_____________________________________________________
# Build the bridge DLL, Allow extension DLLs to call
# back into Pypy space functions
# Do not call this more than once per process
def build_bridge(space):
    "NOT_RPYTHON"
    build_exported_objects()

    export_symbols = list(FUNCTIONS) + SYMBOLS_C + list(GLOBALS)
    from pypy.translator.c.database import LowLevelDatabase
    db = LowLevelDatabase()

    generate_macros(export_symbols, rename=True)
    for obj in GLOBALS.values():
        obj.name = obj.name.replace('Py', 'PyPy')

    # Structure declaration code
    members = []
    structindex = {}
    for name, func in sorted(FUNCTIONS.iteritems()):
        restype, args = c_function_signature(db, func)
        members.append('%s (*%s)(%s);' % (restype, name, args))
        structindex[name] = len(structindex)
    structmembers = '\n'.join(members)
    struct_declaration_code = """\
    struct PyPyAPI {
    %(members)s
    } _pypyAPI;
    struct PyPyAPI* pypyAPI = &_pypyAPI;
    """ % dict(members=structmembers)

    functions = generate_decls_and_callbacks(db)

    global_objects = []
    for obj in GLOBALS.values():
        global_objects.extend(obj.get_global_code_for_bridge())
    global_code = '\n'.join(global_objects)

    prologue = "#include <Python.h>\n"
    code = (prologue +
            struct_declaration_code +
            global_code +
            '\n' +
            '\n'.join(functions))

    eci = build_eci(True, export_symbols, code)
    eci = eci.compile_shared_lib(
        outputfilename=str(udir / "module_cache" / "pypyapi"))
    modulename = py.path.local(eci.libraries[-1])

    run_bootstrap_functions(space)

    # load the bridge, and init structure
    import ctypes
    bridge = ctypes.CDLL(str(modulename), mode=ctypes.RTLD_GLOBAL)

    # populate static data
    for name, obj in GLOBALS.iteritems():
        value = obj.eval(space)
        INTERPLEVEL_API[name] = value
        obj.set_value_in_ctypes_dll(space, bridge, value)

    pypyAPI = ctypes.POINTER(ctypes.c_void_p).in_dll(bridge, 'pypyAPI')

    # implement structure initialization code
    for name, func in FUNCTIONS.iteritems():
        if name.startswith('cpyext_'): # XXX hack
            continue
        pypyAPI[structindex[name]] = ctypes.cast(
            ll2ctypes.lltype2ctypes(func.get_llpointer(space)),
            ctypes.c_void_p)

    setup_init_functions(eci)
    return modulename.new(ext='')

def generate_macros(export_symbols, rename=True):
    "NOT_RPYTHON"
    pypy_macros = []
    renamed_symbols = []
    for name in export_symbols:
        if name.startswith("PyPy"):
            renamed_symbols.append(name)
            continue
        if not rename:
            continue
        newname = name.replace('Py', 'PyPy')
        if not rename:
            newname = name
        pypy_macros.append('#define %s %s' % (name, newname))
        if name.startswith("PyExc_"):
            pypy_macros.append('#define _%s _%s' % (name, newname))
        renamed_symbols.append(newname)
    if rename:
        export_symbols[:] = renamed_symbols

    # Generate defines
    for macro_name, size in [
        ("SIZEOF_LONG_LONG", rffi.LONGLONG),
        ("SIZEOF_VOID_P", rffi.VOIDP),
        ("SIZEOF_SIZE_T", rffi.SIZE_T),
        ("SIZEOF_LONG", rffi.LONG),
        ("SIZEOF_SHORT", rffi.SHORT),
        ("SIZEOF_INT", rffi.INT)
    ]:
        pypy_macros.append("#define %s %s" % (macro_name, rffi.sizeof(size)))
    
    pypy_macros_h = udir.join('pypy_macros.h')
    pypy_macros_h.write('\n'.join(pypy_macros))

def generate_decls_and_callbacks(db, api_struct=True):
    "NOT_RPYTHON"
    # implement function callbacks and generate function decls
    functions = []
    pypy_decls = []
    pypy_decls.append("#ifndef PYPY_STANDALONE\n")
    pypy_decls.append("#ifdef __cplusplus")
    pypy_decls.append("extern \"C\" {")
    pypy_decls.append("#endif\n")

    for decl in FORWARD_DECLS:
        pypy_decls.append("%s;" % (decl,))

    for name, func in sorted(FUNCTIONS.iteritems()):
        restype, args = c_function_signature(db, func)
        pypy_decls.append("PyAPI_FUNC(%s) %s(%s);" % (restype, name, args))
        if api_struct:
            callargs = ', '.join('arg%d' % (i,)
                                 for i in range(len(func.argtypes)))
            if func.restype is lltype.Void:
                body = "{ _pypyAPI.%s(%s); }" % (name, callargs)
            else:
                body = "{ return _pypyAPI.%s(%s); }" % (name, callargs)
            functions.append('%s %s(%s)\n%s' % (restype, name, args, body))

    for obj in GLOBALS.values():
        pypy_decls.append(obj.get_data_declaration())

    pypy_decls.append("#ifdef __cplusplus")
    pypy_decls.append("}")
    pypy_decls.append("#endif")
    pypy_decls.append("#endif /*PYPY_STANDALONE*/\n")

    pypy_decl_h = udir.join('pypy_decl.h')
    pypy_decl_h.write('\n'.join(pypy_decls))
    return functions

def build_eci(building_bridge, export_symbols, code):
    "NOT_RPYTHON"
    # Build code and get pointer to the structure
    kwds = {}
    export_symbols_eci = export_symbols[:]

    compile_extra=['-DPy_BUILD_CORE']

    if building_bridge:
        if sys.platform == "win32":
            # '%s' undefined; assuming extern returning int
            compile_extra.append("/we4013")
        else:
            compile_extra.append("-Werror=implicit-function-declaration")
        export_symbols_eci.append('pypyAPI')
    else:
        kwds["includes"] = ['Python.h'] # this is our Python.h

    # Generate definitions for global structures
    struct_file = udir.join('pypy_structs.c')
    structs = ["#include <Python.h>"]
    for obj in GLOBALS.values():
        structs.extend(obj.get_data_definition())
    struct_file.write('\n'.join(structs))

    eci = ExternalCompilationInfo(
        include_dirs=include_dirs,
        separate_module_files=[source_dir / "varargwrapper.c",
                               source_dir / "pyerrors.c",
                               source_dir / "modsupport.c",
                               source_dir / "getargs.c",
                               source_dir / "stringobject.c",
                               source_dir / "mysnprintf.c",
                               source_dir / "pythonrun.c",
                               source_dir / "bufferobject.c",
                               source_dir / "object.c",
                               source_dir / "cobject.c",
                               struct_file,
                               ],
        separate_module_sources = [code],
        export_symbols=export_symbols_eci,
        compile_extra=compile_extra,
        **kwds
        )
    return eci


def setup_library(space):
    "NOT_RPYTHON"
    build_exported_objects()

    export_symbols = list(FUNCTIONS) + SYMBOLS_C + list(GLOBALS)
    from pypy.translator.c.database import LowLevelDatabase
    db = LowLevelDatabase()

    generate_macros(export_symbols, rename=False)

    functions = generate_decls_and_callbacks(db, api_struct=False)
    code = "#include <Python.h>\n" + "\n".join(functions)

    eci = build_eci(False, export_symbols, code)

    run_bootstrap_functions(space)

    # populate static data
    for obj in GLOBALS.values():
        name = obj.get_name_for_structnode()
        struct = obj.get_value_for_structnode(space, obj.eval(space))
        struct._compilation_info = eci
        export_struct(name, struct)

    for name, func in FUNCTIONS.iteritems():
        deco = entrypoint("cpyext", func.argtypes, name, relax=True)
        deco(func._get_wrapper(space))

    setup_init_functions(eci)
    copy_header_files()

initfunctype = lltype.Ptr(lltype.FuncType([], lltype.Void))
@unwrap_spec(ObjSpace, str, str)
def load_extension_module(space, path, name):
    from pypy.module.cpyext.state import State
    from pypy.module.cpyext.gateway import generic_cpy_call
    state = space.fromcache(State)
    state.package_context = name
    try:
        from pypy.rlib import rdynload
        try:
            ll_libname = rffi.str2charp(path)
            dll = rdynload.dlopen(ll_libname)
            lltype.free(ll_libname, flavor='raw')
        except rdynload.DLOpenError, e:
            raise operationerrfmt(
                space.w_ImportError,
                "unable to load extension module '%s': %s",
                path, e.msg)
        try:
            initptr = rdynload.dlsym(dll, 'init%s' % (name.split('.')[-1],))
        except KeyError:
            raise operationerrfmt(
                space.w_ImportError,
                "function init%s not found in library %s",
                name, path)
        initfunc = rffi.cast(initfunctype, initptr)
        generic_cpy_call(space, initfunc)
        state.check_and_raise_exception()
    finally:
        state.package_context = None

