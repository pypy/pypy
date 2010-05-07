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
from pypy.tool.udir import udir
from pypy.translator import platform
from pypy.module.cpyext.state import State
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.gateway import ObjSpace, unwrap_spec
from pypy.interpreter.nestedscope import Cell
from pypy.rlib.entrypoint import entrypoint
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.objectmodel import specialize
from pypy.rlib.exports import export_struct
from pypy.module import exceptions
from pypy.module.exceptions import interp_exceptions
# CPython 2.4 compatibility
from py.builtin import BaseException
from pypy.tool.sourcetools import func_with_new_name
from pypy.rpython.lltypesystem.lloperation import llop

DEBUG_WRAPPER = True

# update these for other platforms
Py_ssize_t = lltype.Signed
Py_ssize_tP = lltype.Ptr(lltype.Array(Py_ssize_t, hints={'nolength': True}))
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

def copy_header_files():
    for name in ("pypy_decl.h", "pypy_macros.h"):
        udir.join(name).copy(interfaces_dir / name)

_NOT_SPECIFIED = object()
CANNOT_FAIL = object()

# The same function can be called in three different contexts:
# (1) from C code
# (2) in the test suite, though the "api" object
# (3) from RPython code, for example in the implementation of another function.
#
# In contexts (2) and (3), a function declaring a PyObject argument type will
# receive a wrapped pypy object if the parameter name starts with 'w_', a
# reference (= rffi pointer) otherwise; conversion is automatic.  Context (2)
# only allows calls with a wrapped object.
#
# Functions with a PyObject return type should return a wrapped object.
#
# Functions may raise exceptions.  In context (3), the exception flows normally
# through the calling function.  In context (1) and (2), the exception is
# caught; if it is an OperationError, it is stored in the thread state; other
# exceptions generate a OperationError(w_SystemError); and the funtion returns
# the error value specifed in the API.
#

class ApiFunction:
    def __init__(self, argtypes, restype, callable, error=_NOT_SPECIFIED):
        self.argtypes = argtypes
        self.restype = restype
        self.functype = lltype.Ptr(lltype.FuncType(argtypes, restype))
        self.callable = callable
        if error is not _NOT_SPECIFIED:
            self.error_value = error

        # extract the signature from the (CPython-level) code object
        from pypy.interpreter import pycode
        argnames, varargname, kwargname = pycode.cpython_code_signature(callable.func_code)

        assert argnames[0] == 'space'
        self.argnames = argnames[1:]
        assert len(self.argnames) == len(self.argtypes)

    def _freeze_(self):
        return True

    def get_llhelper(self, space):
        llh = getattr(self, '_llhelper', None)
        if llh is None:
            llh = llhelper(self.functype, self.get_wrapper(space))
            self._llhelper = llh
        return llh

    @specialize.memo()
    def get_wrapper(self, space):
        wrapper = getattr(self, '_wrapper', None)
        if wrapper is None:
            wrapper = make_wrapper(space, self.callable)
            self._wrapper = wrapper
            wrapper.relax_sig_check = True
        return wrapper

def cpython_api(argtypes, restype, error=_NOT_SPECIFIED,
                external=True, name=None):
    if error is _NOT_SPECIFIED:
        if restype is PyObject:
            error = lltype.nullptr(PyObject.TO)
        elif restype is lltype.Void:
            error = CANNOT_FAIL
    if type(error) is int:
        error = rffi.cast(restype, error)

    def decorate(func):
        if name is None:
            func_name = func.func_name
        else:
            func_name = name
            func = func_with_new_name(func, name)
        api_function = ApiFunction(argtypes, restype, func, error)
        func.api_func = api_function

        assert func_name not in FUNCTIONS
        assert func_name not in FUNCTIONS_STATIC

        if error is _NOT_SPECIFIED:
            raise ValueError("function %s has no return value for exceptions"
                             % func)
        def make_unwrapper(catch_exception):
            names = api_function.argnames
            types_names_enum_ui = unrolling_iterable(enumerate(
                zip(api_function.argtypes,
                    [tp_name.startswith("w_") for tp_name in names])))

            @specialize.ll()
            def unwrapper(space, *args):
                from pypy.module.cpyext.pyobject import Py_DecRef
                from pypy.module.cpyext.pyobject import make_ref, from_ref
                from pypy.module.cpyext.pyobject import BorrowPair
                newargs = ()
                to_decref = []
                assert len(args) == len(api_function.argtypes)
                for i, (ARG, is_wrapped) in types_names_enum_ui:
                    input_arg = args[i]
                    if is_PyObject(ARG) and not is_wrapped:
                        # build a reference
                        if input_arg is None:
                            arg = lltype.nullptr(PyObject.TO)
                        elif isinstance(input_arg, W_Root):
                            ref = make_ref(space, input_arg)
                            to_decref.append(ref)
                            arg = rffi.cast(ARG, ref)
                        else:
                            arg = input_arg
                    elif is_PyObject(ARG) and is_wrapped:
                        # convert to a wrapped object
                        if input_arg is None:
                            arg = input_arg
                        elif isinstance(input_arg, W_Root):
                            arg = input_arg
                        else:
                            arg = from_ref(space, input_arg)
                    else:
                        arg = input_arg
                    newargs += (arg, )
                try:
                    try:
                        res = func(space, *newargs)
                    except OperationError, e:
                        if not catch_exception:
                            raise
                        if not hasattr(api_function, "error_value"):
                            raise
                        state = space.fromcache(State)
                        state.set_exception(e)
                        if restype is PyObject:
                            return None
                        else:
                            return api_function.error_value
                    if res is None:
                        return None
                    elif isinstance(res, BorrowPair):
                        return res.w_borrowed
                    else:
                        return res
                finally:
                    for arg in to_decref:
                        Py_DecRef(space, arg)
            unwrapper.func = func
            unwrapper.api_func = api_function
            unwrapper._always_inline_ = True
            return unwrapper

        unwrapper_catch = make_unwrapper(True)
        unwrapper_raise = make_unwrapper(False)
        if external:
            FUNCTIONS[func_name] = api_function
        else:
            FUNCTIONS_STATIC[func_name] = api_function
        INTERPLEVEL_API[func_name] = unwrapper_catch # used in tests
        return unwrapper_raise # used in 'normal' RPython code.
    return decorate

def cpython_struct(name, fields, forward=None):
    configname = name.replace(' ', '__')
    setattr(CConfig, configname, rffi_platform.Struct(name, fields))
    if forward is None:
        forward = lltype.ForwardReference()
    TYPES[configname] = forward
    return forward

INTERPLEVEL_API = {}
FUNCTIONS = {}
FUNCTIONS_STATIC = {}
SYMBOLS_C = [
    'Py_FatalError', 'PyOS_snprintf', 'PyOS_vsnprintf', 'PyArg_Parse',
    'PyArg_ParseTuple', 'PyArg_UnpackTuple', 'PyArg_ParseTupleAndKeywords',
    '_PyArg_NoKeywords',
    'PyString_FromFormat', 'PyString_FromFormatV',
    'PyModule_AddObject', 'PyModule_AddIntConstant', 'PyModule_AddStringConstant',
    'Py_BuildValue', 'PyTuple_Pack', 'PyErr_Format', 'PyErr_NewException',

    'PyEval_CallFunction', 'PyEval_CallMethod', 'PyObject_CallFunction',
    'PyObject_CallMethod', 'PyObject_CallFunctionObjArgs', 'PyObject_CallMethodObjArgs',

    'PyBuffer_FromMemory', 'PyBuffer_FromReadWriteMemory', 'PyBuffer_FromObject',
    'PyBuffer_FromReadWriteObject', 'PyBuffer_New', 'PyBuffer_Type', 'init_bufferobject',

    'PyCObject_FromVoidPtr', 'PyCObject_FromVoidPtrAndDesc', 'PyCObject_AsVoidPtr',
    'PyCObject_GetDesc', 'PyCObject_Import', 'PyCObject_SetVoidPtr',
    'PyCObject_Type', 'init_pycobject',

    'PyObject_AsReadBuffer', 'PyObject_AsWriteBuffer', 'PyObject_CheckReadBuffer',
]
TYPES = {}
GLOBALS = { # this needs to include all prebuilt pto, otherwise segfaults occur
    '_Py_NoneStruct#': ('PyObject*', 'space.w_None'),
    '_Py_TrueStruct#': ('PyObject*', 'space.w_True'),
    '_Py_ZeroStruct#': ('PyObject*', 'space.w_False'),
    '_Py_NotImplementedStruct#': ('PyObject*', 'space.w_NotImplemented'),
    }
FORWARD_DECLS = []
INIT_FUNCTIONS = []
BOOTSTRAP_FUNCTIONS = []

def build_exported_objects():
    # Standard exceptions
    for exc_name in exceptions.Module.interpleveldefs.keys():
        GLOBALS['PyExc_' + exc_name] = (
            'PyTypeObject*',
            'space.gettypeobject(interp_exceptions.W_%s.typedef)'% (exc_name, ))

    # Common types with their own struct
    for cpyname, pypyexpr in {
        "Type": "space.w_type",
        "String": "space.w_str",
        "Unicode": "space.w_unicode",
        "BaseString": "space.w_basestring",
        "Dict": "space.w_dict",
        "Tuple": "space.w_tuple",
        "List": "space.w_list",
        "Int": "space.w_int",
        "Bool": "space.w_bool",
        "Float": "space.w_float",
        "Long": "space.w_long",
        "Complex": "space.w_complex",
        "BaseObject": "space.w_object",
        'None': 'space.type(space.w_None)',
        'NotImplemented': 'space.type(space.w_NotImplemented)',
        'Cell': 'space.gettypeobject(Cell.typedef)',
        }.items():
        GLOBALS['Py%s_Type#' % (cpyname, )] = ('PyTypeObject*', pypyexpr)

    for cpyname in 'Method List Int Long Dict Tuple'.split():
        FORWARD_DECLS.append('typedef struct { PyObject_HEAD } '
                             'Py%sObject' % (cpyname, ))
build_exported_objects()

def get_structtype_for_ctype(ctype):
    from pypy.module.cpyext.typeobjectdefs import PyTypeObjectPtr
    return {"PyObject*": PyObject, "PyTypeObject*": PyTypeObjectPtr}[ctype]

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

@specialize.memo()
def is_PyObject(TYPE):
    if not isinstance(TYPE, lltype.Ptr):
        return False
    return hasattr(TYPE.TO, 'c_ob_refcnt') and hasattr(TYPE.TO, 'c_ob_type')

# a pointer to PyObject
PyObjectP = rffi.CArrayPtr(PyObject)

VA_TP_LIST = {}
#{'int': lltype.Signed,
#              'PyObject*': PyObject,
#              'PyObject**': PyObjectP,
#              'int*': rffi.INTP}

def configure_types():
    for name, TYPE in rffi_platform.configure(CConfig).iteritems():
        if name in TYPES:
            TYPES[name].become(TYPE)

def build_type_checkers(type_name, cls=None):
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
    @cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL, name=check_name)
    def check(space, w_obj):
        w_obj_type = space.type(w_obj)
        w_type = get_w_type(space)
        return int(space.is_w(w_obj_type, w_type) or
                   space.is_true(space.issubtype(w_obj_type, w_type)))
    @cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL,
                 name=check_name + "Exact")
    def check_exact(space, w_obj):
        w_obj_type = space.type(w_obj)
        w_type = get_w_type(space)
        return int(space.is_w(w_obj_type, w_type))
    return check, check_exact

pypy_debug_catch_fatal_exception = rffi.llexternal('pypy_debug_catch_fatal_exception', [], lltype.Void)

# Make the wrapper for the cases (1) and (2)
def make_wrapper(space, callable):
    names = callable.api_func.argnames
    argtypes_enum_ui = unrolling_iterable(enumerate(zip(callable.api_func.argtypes,
        [name.startswith("w_") for name in names])))
    fatal_value = callable.api_func.restype._defl()

    @specialize.ll()
    def wrapper(*args):
        from pypy.module.cpyext.pyobject import make_ref, from_ref
        from pypy.module.cpyext.pyobject import BorrowPair
        # we hope that malloc removal removes the newtuple() that is
        # inserted exactly here by the varargs specializer
        llop.gc_stack_bottom(lltype.Void)   # marker for trackgcroot.py
        rffi.stackcounter.stacks_counter += 1
        retval = fatal_value
        boxed_args = ()
        try:
            if not we_are_translated() and DEBUG_WRAPPER:
                print >>sys.stderr, callable,
            assert len(args) == len(callable.api_func.argtypes)
            for i, (typ, is_wrapped) in argtypes_enum_ui:
                arg = args[i]
                if typ is PyObject and is_wrapped:
                    if arg:
                        arg_conv = from_ref(space, arg)
                    else:
                        arg_conv = None
                else:
                    arg_conv = arg
                boxed_args += (arg_conv, )
            state = space.fromcache(State)
            try:
                result = callable(space, *boxed_args)
                if not we_are_translated() and DEBUG_WRAPPER:
                    print >>sys.stderr, " DONE"
            except OperationError, e:
                failed = True
                state.set_exception(e)
            except BaseException, e:
                failed = True
                state.set_exception(OperationError(space.w_SystemError,
                                                   space.wrap(str(e))))
                if not we_are_translated():
                    import traceback
                    traceback.print_exc()
            else:
                failed = False

            if failed:
                error_value = callable.api_func.error_value
                if error_value is CANNOT_FAIL:
                    raise SystemError("The function '%s' was not supposed to fail"
                                      % (callable.__name__,))
                retval = error_value

            elif callable.api_func.restype is PyObject:
                if result is None:
                    retval = make_ref(space, None)
                elif isinstance(result, BorrowPair):
                    retval = result.get_ref(space)
                elif not rffi._isllptr(result):
                    retval = make_ref(space, result)
                else:
                    retval = result
            elif callable.api_func.restype is not lltype.Void:
                retval = rffi.cast(callable.api_func.restype, result)
        except Exception, e:
            if not we_are_translated():
                import traceback
                traceback.print_exc()
                print str(e)
                # we can't do much here, since we're in ctypes, swallow
            else:
                pypy_debug_catch_fatal_exception()
        rffi.stackcounter.stacks_counter -= 1
        return retval
    callable._always_inline_ = True
    wrapper.__name__ = "wrapper for %r" % (callable, )
    return wrapper

def process_va_name(name):
    return name.replace('*', '_star')

def setup_va_functions(eci):
    for name, TP in VA_TP_LIST.iteritems():
        name_no_star = process_va_name(name)
        func = rffi.llexternal('pypy_va_get_%s' % name_no_star, [VA_LIST_P],
                               TP, compilation_info=eci)
        globals()['va_get_%s' % name_no_star] = func

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

#_____________________________________________________
# Build the bridge DLL, Allow extension DLLs to call
# back into Pypy space functions
# Do not call this more than once per process
def build_bridge(space):
    from pypy.module.cpyext.pyobject import make_ref

    export_symbols = list(FUNCTIONS) + SYMBOLS_C + list(GLOBALS)
    from pypy.translator.c.database import LowLevelDatabase
    db = LowLevelDatabase()

    generate_macros(export_symbols, rename=True, do_deref=True)

    # Structure declaration code
    members = []
    structindex = {}
    for name, func in FUNCTIONS.iteritems():
        cdecl = db.gettype(func.functype)
        members.append(cdecl.replace('@', name) + ';')
        structindex[name] = len(structindex)
    structmembers = '\n'.join(members)
    struct_declaration_code = """\
    struct PyPyAPI {
    %(members)s
    } _pypyAPI;
    struct PyPyAPI* pypyAPI = &_pypyAPI;
    """ % dict(members=structmembers)

    functions = generate_decls_and_callbacks(db, export_symbols)

    global_objects = []
    for name, (type, expr) in GLOBALS.iteritems():
        global_objects.append('%s %s = NULL;' % (type, name.replace("#", "")))
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
    pypyAPI = ctypes.POINTER(ctypes.c_void_p).in_dll(bridge, 'pypyAPI')

    # populate static data
    for name, (type, expr) in GLOBALS.iteritems():
        w_obj = eval(expr)
        name = name.replace("#", "")
        INTERPLEVEL_API[name] = w_obj

        name = name.replace('Py', 'PyPy')
        ptr = ctypes.c_void_p.in_dll(bridge, name)
        ptr.value = ctypes.cast(ll2ctypes.lltype2ctypes(make_ref(space, w_obj)),
            ctypes.c_void_p).value

    # implement structure initialization code
    for name, func in FUNCTIONS.iteritems():
        pypyAPI[structindex[name]] = ctypes.cast(
            ll2ctypes.lltype2ctypes(func.get_llhelper(space)),
            ctypes.c_void_p)

    setup_va_functions(eci)
   
    setup_init_functions(eci)
    return modulename.new(ext='')

def generate_macros(export_symbols, rename=True, do_deref=True):
    pypy_macros = []
    renamed_symbols = []
    for name in export_symbols:
        if name.startswith("PyPy"):
            renamed_symbols.append(name)
            continue
        if "#" in name:
            deref = "*"
            if not do_deref and not rename: continue
        else:
            deref = ""
            if not rename: continue
        name = name.replace("#", "")
        newname = name.replace('Py', 'PyPy')
        if not rename:
            newname = name
        pypy_macros.append('#define %s %s%s' % (name, deref, newname))
        renamed_symbols.append(newname)
    if rename:
        export_symbols[:] = renamed_symbols
    else:
        export_symbols[:] = [sym.replace("#", "") for sym in export_symbols]
    
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

def generate_decls_and_callbacks(db, export_symbols, api_struct=True, globals_are_pointers=True):
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
        pypy_decls.append("PyAPI_FUNC(%s) %s(%s);" % (restype, name, args))
        if api_struct:
            callargs = ', '.join('arg%d' % (i,)
                                 for i in range(len(func.argtypes)))
            body = "{ return _pypyAPI.%s(%s); }" % (name, callargs)
            functions.append('%s %s(%s)\n%s' % (restype, name, args, body))
    for name in VA_TP_LIST:
        name_no_star = process_va_name(name)
        header = ('%s pypy_va_get_%s(va_list* vp)' %
                  (name, name_no_star))
        pypy_decls.append(header + ';')
        functions.append(header + '\n{return va_arg(*vp, %s);}\n' % name)
        export_symbols.append('pypy_va_get_%s' % (name_no_star,))

    for name, (typ, expr) in GLOBALS.iteritems():
        name_clean = name.replace("#", "")
        if not globals_are_pointers:
            typ = typ.replace("*", "")
        pypy_decls.append('PyAPI_DATA(%s) %s;' % (typ, name_clean))
        if not globals_are_pointers and "#" not in name:
            pypy_decls.append("#define %s (PyObject*)&%s" % (name, name,))

    pypy_decls.append("#ifdef __cplusplus")
    pypy_decls.append("}")
    pypy_decls.append("#endif")
    pypy_decls.append("#endif /*PYPY_STANDALONE*/\n")

    pypy_decl_h = udir.join('pypy_decl.h')
    pypy_decl_h.write('\n'.join(pypy_decls))
    return functions

def build_eci(building_bridge, export_symbols, code):
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
                               ],
        separate_module_sources = [code],
        export_symbols=export_symbols_eci,
        compile_extra=compile_extra,
        **kwds
        )
    return eci


def setup_library(space):
    from pypy.module.cpyext.pyobject import make_ref

    export_symbols = list(FUNCTIONS) + SYMBOLS_C + list(GLOBALS)
    from pypy.translator.c.database import LowLevelDatabase
    db = LowLevelDatabase()

    generate_macros(export_symbols, rename=False, do_deref=False)

    functions = generate_decls_and_callbacks(db, [], api_struct=False, globals_are_pointers=False)
    code = "#include <Python.h>\n" + "\n".join(functions)

    eci = build_eci(False, export_symbols, code)

    run_bootstrap_functions(space)
    setup_va_functions(eci)

    # populate static data
    for name, (type, expr) in GLOBALS.iteritems():
        name = name.replace("#", "")
        w_obj = eval(expr)
        struct_ptr = make_ref(space, w_obj)
        struct = rffi.cast(get_structtype_for_ctype(type), struct_ptr)._obj
        struct._compilation_info = eci
        export_struct(name, struct)

    for name, func in FUNCTIONS.iteritems():
        deco = entrypoint("cpyext", func.argtypes, name, relax=True)
        deco(func.get_wrapper(space))
    for name, func in FUNCTIONS_STATIC.iteritems():
        func.get_wrapper(space).c_name = name

    setup_init_functions(eci)
    copy_header_files()

initfunctype = lltype.Ptr(lltype.FuncType([], lltype.Void))
@unwrap_spec(ObjSpace, str, str)
def load_extension_module(space, path, name):
    state = space.fromcache(State)
    state.package_context = name
    try:
        from pypy.rlib import libffi
        try:
            dll = libffi.CDLL(path, False)
        except libffi.DLOpenError, e:
            raise operationerrfmt(
                space.w_ImportError,
                "unable to load extension module '%s': %s",
                path, e.msg)
        try:
            initptr = libffi.dlsym(dll.lib, 'init%s' % (name.split('.')[-1],))
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

@specialize.ll()
def generic_cpy_call(space, func, *args):
    FT = lltype.typeOf(func).TO
    return make_generic_cpy_call(FT, True, False)(space, func, *args)

@specialize.ll()
def generic_cpy_call_dont_decref(space, func, *args):
    FT = lltype.typeOf(func).TO
    return make_generic_cpy_call(FT, False, False)(space, func, *args)

@specialize.ll()    
def generic_cpy_call_expect_null(space, func, *args):
    FT = lltype.typeOf(func).TO
    return make_generic_cpy_call(FT, True, True)(space, func, *args)

@specialize.memo()
def make_generic_cpy_call(FT, decref_args, expect_null):
    from pypy.module.cpyext.pyobject import make_ref, from_ref, Py_DecRef
    from pypy.module.cpyext.pyerrors import PyErr_Occurred
    unrolling_arg_types = unrolling_iterable(enumerate(FT.ARGS))
    RESULT_TYPE = FT.RESULT

    # copied and modified from rffi.py
    # We need tons of care to ensure that no GC operation and no
    # exception checking occurs in call_external_function.
    argnames = ', '.join(['a%d' % i for i in range(len(FT.ARGS))])
    source = py.code.Source("""
        def call_external_function(funcptr, %(argnames)s):
            # NB. it is essential that no exception checking occurs here!
            res = funcptr(%(argnames)s)
            return res
    """ % locals())
    miniglobals = {'__name__':    __name__, # for module name propagation
                   }
    exec source.compile() in miniglobals
    call_external_function = miniglobals['call_external_function']
    call_external_function._dont_inline_ = True
    call_external_function._annspecialcase_ = 'specialize:ll'
    call_external_function._gctransformer_hint_close_stack_ = True
    call_external_function = func_with_new_name(call_external_function,
                                                'ccall_' + name)
    # don't inline, as a hack to guarantee that no GC pointer is alive
    # anywhere in call_external_function

    @specialize.ll()
    def generic_cpy_call(space, func, *args):
        boxed_args = ()
        to_decref = []
        assert len(args) == len(FT.ARGS)
        for i, ARG in unrolling_arg_types:
            arg = args[i]
            if ARG is PyObject:
                if arg is None:
                    boxed_args += (lltype.nullptr(PyObject.TO),)
                elif isinstance(arg, W_Root):
                    ref = make_ref(space, arg)
                    boxed_args += (ref,)
                    if decref_args:
                        to_decref.append(ref)
                else:
                    boxed_args += (arg,)
            else:
                boxed_args += (arg,)
        result = call_external_function(func, *boxed_args)
        try:
            if RESULT_TYPE is PyObject:
                if result is None:
                    ret = result
                elif isinstance(result, W_Root):
                    ret = result
                else:
                    ret = from_ref(space, result)
                    # The object reference returned from a C function
                    # that is called from Python must be an owned reference
                    # - ownership is transferred from the function to its caller.
                    if result:
                        Py_DecRef(space, result)

                # Check for exception consistency
                has_error = PyErr_Occurred(space) is not None
                has_result = ret is not None
                if has_error and has_result:
                    raise OperationError(space.w_SystemError, space.wrap(
                        "An exception was set, but function returned a value"))
                elif not expect_null and not has_error and not has_result:
                    raise OperationError(space.w_SystemError, space.wrap(
                        "Function returned a NULL result without setting an exception"))

                if has_error:
                    state = space.fromcache(State)
                    state.check_and_raise_exception()

                return ret
            return result
        finally:
            if decref_args:
                for ref in to_decref:
                    Py_DecRef(space, ref)
    return generic_cpy_call

