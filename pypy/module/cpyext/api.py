import py
import autopath
import ctypes

from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.tool import rffi_platform
from pypy.rpython.lltypesystem import ll2ctypes
from pypy.rpython.annlowlevel import llhelper
from pypy.translator.c.database import LowLevelDatabase
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.tool.udir import udir
from pypy.translator import platform
from pypy.module.cpyext.state import State


include_dirs = [
    py.path.local(autopath.pypydir).join('module', 'cpyext', 'include'),
    udir,
    ]

class CConfig:
    _compilation_info_ = ExternalCompilationInfo(
        include_dirs=include_dirs,
        includes=['Python.h']
        )

class ApiFunction:
    def __init__(self, argtypes, restype, callable):
        self.argtypes = argtypes
        self.restype = restype
        self.functype = lltype.Ptr(lltype.FuncType(argtypes, restype))
        self.callable = callable

def cpython_api(argtypes, restype):
    def decorate(func):
        api_function = ApiFunction(argtypes, restype, func)
        FUNCTIONS[func.func_name] = api_function
        func.api_func = api_function
        return func
    return decorate

def cpython_struct(name, fields):
    configname = name.replace(' ', '__')
    setattr(CConfig, configname, rffi_platform.Struct(name, fields))
    forward = lltype.ForwardReference()
    TYPES[configname] = forward
    return forward

FUNCTIONS = {}
TYPES = {}

# It is important that these PyObjects are allocated in a raw fashion
# Thus we cannot save a forward pointer to the wrapped object
# So we need a forward and backward mapping in our State instance
PyObject = lltype.Ptr(cpython_struct('struct _object', [("refcnt", lltype.Signed)]))

def configure():
    for name, TYPE in rffi_platform.configure(CConfig).iteritems():
        TYPES[name].become(TYPE)

def make_ref(space, w_obj):
    state = space.fromcache(State)
    py_obj = state.py_objects_w2r.get(w_obj)
    if py_obj is None:
        py_obj = lltype.malloc(PyObject.TO, None, flavor="raw")
        py_obj.c_refcnt = 1
        ctypes_obj = ll2ctypes.lltype2ctypes(py_obj)
        ptr = ctypes.cast(ctypes_obj, ctypes.c_void_p).value
        py_obj = ll2ctypes.ctypes2lltype(PyObject, ctypes_obj)
        state.py_objects_w2r[w_obj] = py_obj
        state.py_objects_r2w[ptr] = w_obj
    return py_obj

def from_ref(space, ref):
    state = space.fromcache(State)
    if not ref:
        raise RuntimeError("Null pointer dereference!")
    ptr = ctypes.addressof(ref._obj._storage)
    try:
        obj = state.py_objects_r2w[ptr]
    except KeyError:
        raise RuntimeError("Got invalid reference to a PyObject")
    return obj

#_____________________________________________________
# Build the bridge DLL, Allow extension DLLs to call
# back into Pypy space functions
def build_bridge(space, rename=True):
    db = LowLevelDatabase()

    export_symbols = list(FUNCTIONS)

    structindex = {}

    prologue = """\
    #define const            /* cheat */
    #include <Python.h>
    #define long int         /* cheat */
    """
    if rename:
        pypy_rename = []
        export_symbols = []
        for name in FUNCTIONS:
            newname = name.replace('Py', 'PyPy')
            pypy_rename.append('#define %s %s' % (name, newname))
            export_symbols.append(newname)
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

    global_objects = """
    PyObject *PyPy_None = NULL;
    """
    code = (prologue +
            struct_declaration_code +
            global_objects +
            '\n' +
            '\n'.join(functions))

    # Build code and get pointer to the structure
    eci = ExternalCompilationInfo(
        include_dirs=include_dirs,
        separate_module_sources=[code],
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
    Py_NONE = ctypes.c_void_p.in_dll(bridge, 'PyPy_None')

    def make_wrapper(callable):
        def wrapper(*args):
            boxed_args = []
            # XXX use unrolling_iterable here
            for typ, arg in zip(callable.api_func.argtypes, args):
                if typ is PyObject:
                    arg = from_ref(space, arg)
                boxed_args.append(arg)
            retval = callable(space, *boxed_args)
            if callable.api_func.restype is PyObject:
                retval = make_ref(space, retval)
            return retval
        return wrapper

    # implement structure initialization code
    for name, func in FUNCTIONS.iteritems():
        pypyAPI[structindex[name]] = ctypes.cast(
            ll2ctypes.lltype2ctypes(llhelper(func.functype, make_wrapper(func.callable))),
            ctypes.c_void_p)
    Py_NONE.value = ctypes.cast(ll2ctypes.lltype2ctypes(make_ref(space, space.w_None)),
            ctypes.c_void_p).value

    return modulename.new(ext='')

