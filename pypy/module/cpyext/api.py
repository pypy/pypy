import ctypes
import sys

import py

from pypy.translator.goal import autopath
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.tool import rffi_platform
from pypy.rpython.lltypesystem import ll2ctypes
from pypy.rpython.annlowlevel import llhelper
from pypy.translator.c.database import LowLevelDatabase
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.tool.udir import udir
from pypy.translator import platform
from pypy.module.cpyext.state import State
from pypy.interpreter.error import OperationError


Py_ssize_t = lltype.Signed

include_dir = py.path.local(autopath.pypydir).join('module', 'cpyext', 'include')
include_dirs = [
    include_dir,
    udir,
    ]

class CConfig:
    _compilation_info_ = ExternalCompilationInfo(
        include_dirs=include_dirs,
        includes=['Python.h']
        )

class CConfig_constants:
    _compilation_info_ = CConfig._compilation_info_

constant_names = """Py_TPFLAGS_READY Py_TPFLAGS_READYING """.split()
for name in constant_names:
    setattr(CConfig_constants, name, rffi_platform.ConstantInteger(name))
# XXX does not work, why?
#globals().update(rffi_platform.configure(CConfig_constants))
Py_TPFLAGS_READY = (1L<<12)
Py_TPFLAGS_READYING = (1L<<13)
METH_COEXIST = 0x0040
METH_STATIC = 0x0020
METH_CLASS = 0x0010
METH_NOARGS = 0x0004


class ApiFunction:
    def __init__(self, argtypes, restype, callable, borrowed):
        self.argtypes = argtypes
        self.restype = restype
        self.functype = lltype.Ptr(lltype.FuncType(argtypes, restype))
        self.callable = callable
        self.borrowed = borrowed

def cpython_api(argtypes, restype, borrowed=False):
    def decorate(func):
        api_function = ApiFunction(argtypes, restype, func, borrowed)
        FUNCTIONS[func.func_name] = api_function
        func.api_func = api_function
        return func
    return decorate

def cpython_struct(name, fields, forward=None):
    configname = name.replace(' ', '__')
    setattr(CConfig, configname, rffi_platform.Struct(name, fields))
    if forward is None:
        forward = lltype.ForwardReference()
    TYPES[configname] = forward
    return forward

FUNCTIONS = {}
TYPES = {}
GLOBALS = {
    'Py_None': ('PyObject*', 'space.w_None'),
    'Py_True': ('PyObject*', 'space.w_True'),
    'Py_False': ('PyObject*', 'space.w_False'),
    'PyExc_Exception': ('PyObject*', 'space.w_Exception'),
    'PyExc_TypeError': ('PyObject*', 'space.w_TypeError'),
    'PyType_Type': ('PyTypeObject*', 'space.w_type'),
    'PyBaseObject_Type#': ('PyTypeObject*', 'space.w_object'),
    }

# It is important that these PyObjects are allocated in a raw fashion
# Thus we cannot save a forward pointer to the wrapped object
# So we need a forward and backward mapping in our State instance
PyObjectStruct = lltype.ForwardReference()
PyObject = lltype.Ptr(PyObjectStruct)
PyObjectFields = (("obj_refcnt", lltype.Signed), ("obj_type", PyObject))
PyVarObjectFields = PyObjectFields + (("obj_size", Py_ssize_t), )
cpython_struct('struct _object', PyObjectFields, PyObjectStruct)


def configure():
    for name, TYPE in rffi_platform.configure(CConfig).iteritems():
        if name in TYPES:
            TYPES[name].become(TYPE)

class NullPointerException(Exception):
    pass

class InvalidPointerException(Exception):
    pass

def get_padded_type(T, size):
    fields = T._flds.copy()
    hints = T._hints.copy()
    hints["size"] = size
    del hints["fieldoffsets"]
    pad_fields = []
    new_fields = []
    for name in T._names:
        new_fields.append((name, fields[name]))
    for i in xrange(size - rffi.sizeof(T)):
        new_fields.append(("custom%i" % (i, ), lltype.Char))
    hints["padding"] = hints["padding"] + tuple(pad_fields)
    return lltype.Struct(hints["c_name"], *new_fields, hints=hints)

def make_ref(space, w_obj, borrowed=False):
    if w_obj is None:
        return lltype.nullptr(PyObject.TO)
        #raise NullPointerException("Trying to pass a NULL reference")
    state = space.fromcache(State)
    py_obj = state.py_objects_w2r.get(w_obj)
    if py_obj is None:
        from pypy.module.cpyext.typeobject import allocate_type_obj,\
                W_PyCTypeObject, W_PyCObject
        if space.is_w(space.type(w_obj), space.w_type):
            py_obj = allocate_type_obj(space, w_obj)
        elif isinstance(w_obj, W_PyCObject):
            w_type = space.type(w_obj)
            assert isinstance(w_type, W_PyCTypeObject)
            pto = w_type.pto
            basicsize = pto._obj.c_tp_basicsize
            T = get_padded_type(PyObject.TO, basicsize)
            py_obj = lltype.malloc(T, None, flavor="raw")
        else:
            py_obj = lltype.malloc(PyObject.TO, None, flavor="raw")
        py_obj.c_obj_refcnt = 1
        ctypes_obj = ll2ctypes.lltype2ctypes(py_obj)
        ptr = ctypes.cast(ctypes_obj, ctypes.c_void_p).value
        py_obj = ll2ctypes.ctypes2lltype(PyObject, ctypes_obj)
        state.py_objects_w2r[w_obj] = py_obj
        state.py_objects_r2w[ptr] = w_obj
    elif not borrowed:
        py_obj.c_obj_refcnt += 1
    return py_obj

def from_ref(space, ref):
    state = space.fromcache(State)
    if not ref:
        raise NullPointerException("Null pointer dereference!")
    ptr = ctypes.addressof(ref._obj._storage)
    try:
        obj = state.py_objects_r2w[ptr]
    except KeyError:
        import pdb; pdb.set_trace()
        raise InvalidPointerException("Got invalid reference to a PyObject")
    return obj

#_____________________________________________________
# Build the bridge DLL, Allow extension DLLs to call
# back into Pypy space functions
def build_bridge(space, rename=True):
    db = LowLevelDatabase()

    export_symbols = list(FUNCTIONS) + list(GLOBALS)

    structindex = {}

    prologue = """\
    #define const            /* cheat */
    #include <Python.h>
    #define long int         /* cheat */
    """
    if rename:
        pypy_rename = []
        renamed_symbols = []
        for name in export_symbols:
            if "#" in name:
                deref = "*"
            else:
                deref = ""
            name = name.replace("#", "")
            newname = name.replace('Py', 'PyPy')
            pypy_rename.append('#define %s %s%s' % (name, deref, newname))
            renamed_symbols.append(newname)
        export_symbols = renamed_symbols
        pypy_rename_h = udir.join('pypy_rename.h')
        pypy_rename_h.write('\n'.join(pypy_rename))

        prologue = """\
        #include <pypy_rename.h> /* avoid symbol clashes */
        """ + prologue

    # Structure declaration code
    members = []
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

    # implement function callbacks
    functions = []
    for name, func in FUNCTIONS.iteritems():
        restype = db.gettype(func.restype).replace('@', '')
        args = []
        for i, argtype in enumerate(func.argtypes):
            arg = db.gettype(argtype)
            arg = arg.replace('@', 'arg%d' % (i,))
            args.append(arg)
        args = ', '.join(args)
        callargs = ', '.join('arg%d' % (i,) for i in range(len(func.argtypes)))
        header = "%s %s(%s)" % (restype, name, args)
        body = "{ return _pypyAPI.%s(%s); }" % (name, callargs)
        functions.append('%s\n%s\n' % (header, body))

    global_objects = []
    for name, (type, expr) in GLOBALS.iteritems():
        global_objects.append('%s %s = NULL;' % (type, name.replace("#", "")))
    global_code = '\n'.join(global_objects)
    code = (prologue +
            struct_declaration_code +
            global_code +
            '\n' +
            '\n'.join(functions))

    # Build code and get pointer to the structure
    eci = ExternalCompilationInfo(
        include_dirs=include_dirs,
        separate_module_sources=[code],
        separate_module_files=[include_dir / "typeobject.c",
                               include_dir / "varargwrapper.c"],
        export_symbols=['pypyAPI'] + export_symbols,
        )
    eci = eci.convert_sources_to_files()
    modulename = platform.platform.compile(
        [], eci,
        standalone=False)

    # load the bridge, and init structure
    import ctypes
    bridge = ctypes.CDLL(str(modulename))
    pypyAPI = ctypes.POINTER(ctypes.c_void_p).in_dll(bridge, 'pypyAPI')

    # populate static data
    for name, (type, expr) in GLOBALS.iteritems():
        name = name.replace("#", "")
        if rename:
            name = name.replace('Py', 'PyPy')
        w_obj = eval(expr)
        ptr = ctypes.c_void_p.in_dll(bridge, name)
        ptr.value = ctypes.cast(ll2ctypes.lltype2ctypes(make_ref(space, w_obj)),
            ctypes.c_void_p).value

    def make_wrapper(callable):
        def wrapper(*args):
            boxed_args = []
            # XXX use unrolling_iterable here
            print >>sys.stderr, callable
            for i, typ in enumerate(callable.api_func.argtypes):
                arg = args[i]
                if typ is PyObject:
                    arg = from_ref(space, arg)
                boxed_args.append(arg)
            state = space.fromcache(State)
            try:
                retval = callable(space, *boxed_args)
                print "Callable worked"
            except OperationError, e:
                e.normalize_exception(space)
                state.exc_type = e.w_type
                state.exc_value = e.get_w_value(space)
            except BaseException, e:
                state.exc_type = space.w_SystemError
                state.exc_value = space.wrap(str(e))
                import traceback
                traceback.print_exc()

            if state.exc_value is not None:
                restype = callable.api_func.restype
                if restype is lltype.Void:
                    return
                if restype is PyObject:
                    return lltype.nullptr(PyObject.TO)
                if restype in (lltype.Signed, rffi.INT):
                    return -1
                assert False, "Unknown return type"

            if callable.api_func.restype is PyObject:
                retval = make_ref(space, retval, borrowed=callable.api_func.borrowed)
            return retval
        return wrapper

    # implement structure initialization code
    for name, func in FUNCTIONS.iteritems():
        pypyAPI[structindex[name]] = ctypes.cast(
            ll2ctypes.lltype2ctypes(llhelper(func.functype, make_wrapper(func.callable))),
            ctypes.c_void_p)

    return modulename.new(ext='')

def load_extension_module(space, path, name):
    state = space.fromcache(State)
    import ctypes
    initfunc = ctypes.CDLL(path)['init%s' % (name,)]
    initfunc()
    state.check_and_raise_exception()

