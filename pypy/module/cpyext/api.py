from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.tool import rffi_platform
from pypy.rpython.lltypesystem import ll2ctypes
from pypy.rpython.annlowlevel import llhelper
from pypy.translator.c.database import LowLevelDatabase
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator import platform

import py, autopath

include_dir = py.path.local(autopath.pypydir).join(
    'module', 'cpyext', 'include')

class CConfig:
    _compilation_info_ = ExternalCompilationInfo(
        include_dirs=[include_dir],
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
        FUNCTIONS[func.func_name] = ApiFunction(argtypes, restype, func)
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

PyObject = lltype.Ptr(cpython_struct('struct _object', []))

def configure():
    for name, TYPE in rffi_platform.configure(CConfig).iteritems():
        TYPES[name].become(TYPE)

def make_ref(w_obj):
    return lltype.nullptr(PyObject.TO) # XXX for the moment

def from_ref(space, ref):
    if not ref:
        return space.w_None # XXX for the moment, should be an exception
    assert False

#_____________________________________________________
# Build the bridge DLL, Allow extension DLLs to call
# back into Pypy space functions
def build_bridge(space):
    db = LowLevelDatabase()

    structindex = {}

    # Structure declaration code
    members = []
    for name, func in FUNCTIONS.iteritems():
        cdecl = db.gettype(func.functype)
        members.append(cdecl.replace('@', name) + ';')
        structindex[name] = len(structindex)
    structmembers = '\n'.join(members)
    struct_declaration_code = """\
    #define const       /* cheat */
    #include <Python.h>
    #define long int    /* cheat */
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

    code = struct_declaration_code + '\n' + '\n'.join(functions)

    # Build code and get pointer to the structure
    eci = ExternalCompilationInfo(
        include_dirs=[include_dir],
        separate_module_sources=[code],
        export_symbols=['pypyAPI'] + list(FUNCTIONS),
        )
    eci = eci.convert_sources_to_files()
    modulename = platform.platform.compile(
        [], eci,
        standalone=False)

    # load the bridge, and init structure
    import ctypes
    bridge = ctypes.CDLL(str(modulename))
    pypyAPI = ctypes.POINTER(ctypes.c_void_p).in_dll(bridge, 'pypyAPI')

    def make_wrapper(callable):
        def wrapper(*args):
            return callable(space, *args)
        return wrapper

    # implement structure initialization code
    for name, func in FUNCTIONS.iteritems():
        pypyAPI[structindex[name]] = ctypes.cast(
            ll2ctypes.lltype2ctypes(llhelper(func.functype, make_wrapper(func.callable))),
            ctypes.c_void_p)

    return modulename.new(ext='')

