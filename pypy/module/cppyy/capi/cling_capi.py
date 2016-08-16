import py, os

from pypy.interpreter.gateway import interp2app, unwrap_spec

from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib import libffi, rdynload

from pypy.module.cppyy.capi.capi_types import C_OBJECT

__all__ = ['identify', 'std_string_name', 'eci', 'c_load_dictionary']

pkgpath = py.path.local(__file__).dirpath().join(os.pardir)
srcpath = pkgpath.join("src")
incpath = pkgpath.join("include")

import commands
(config_stat, incdir) = commands.getstatusoutput("root-config --incdir")

if os.environ.get("ROOTSYS"):
    if config_stat != 0:     # presumably Reflex-only
        rootincpath = [os.path.join(os.environ["ROOTSYS"], "interpreter/cling/include"),
                       os.path.join(os.environ["ROOTSYS"], "interpreter/llvm/inst/include"),
                       os.path.join(os.environ["ROOTSYS"], "include"),]
        rootlibpath = [os.path.join(os.environ["ROOTSYS"], "lib64"), os.path.join(os.environ["ROOTSYS"], "lib")]
    else:
        rootincpath = [incdir]
        rootlibpath = commands.getoutput("root-config --libdir").split()
else:
    if config_stat == 0:
        rootincpath = [incdir]
        rootlibpath = commands.getoutput("root-config --libdir").split()
    else:
        rootincpath = []
        rootlibpath = []

def identify():
    return 'Cling'

ts_reflect = False
ts_call    = 'auto'
ts_memory  = 'auto'
ts_helper  = 'auto'

std_string_name = 'std::basic_string<char>'

# force loading (and exposure) of libCore symbols
with rffi.scoped_str2charp('libCore.so') as ll_libname:
    _coredll = rdynload.dlopen(ll_libname, rdynload.RTLD_GLOBAL | rdynload.RTLD_NOW)

# require local translator path to pickup common defs
from rpython.translator import cdir
translator_c_dir = py.path.local(cdir)

eci = ExternalCompilationInfo(
    separate_module_files=[srcpath.join("clingcwrapper.cxx")],
    include_dirs=[incpath, translator_c_dir] + rootincpath,
    includes=["clingcwrapper.h"],
    library_dirs=rootlibpath,
    libraries=["Cling"],
    compile_extra=["-fno-strict-aliasing", "-std=c++14"],
    use_cpp_linker=True,
)

_c_load_dictionary = rffi.llexternal(
    "cppyy_load_dictionary",
    [rffi.CCHARP], rdynload.DLLHANDLE,
    releasegil=False,
    compilation_info=eci)

def c_load_dictionary(name):
    pch = _c_load_dictionary(name)
    return pch

_c_stdstring2charp = rffi.llexternal(
    "cppyy_stdstring2charp",
    [C_OBJECT, rffi.SIZE_TP], rffi.CCHARP,
    releasegil=ts_helper,
    compilation_info=eci)
def c_stdstring2charp(space, cppstr):
    sz = lltype.malloc(rffi.SIZE_TP.TO, 1, flavor='raw')
    try:
        cstr = _c_stdstring2charp(cppstr, sz)
        cstr_len = int(sz[0])
    finally:
        lltype.free(sz, flavor='raw')
    return rffi.charpsize2str(cstr, cstr_len)

# TODO: factor these out ...
# pythonizations
def stdstring_c_str(space, w_self):
    """Return a python string taking into account \0"""

    from pypy.module.cppyy import interp_cppyy
    cppstr = space.interp_w(interp_cppyy.W_CPPInstance, w_self, can_be_None=False)
    return space.wrap(c_stdstring2charp(space, cppstr._rawobject))

# setup pythonizations for later use at run-time
_pythonizations = {}
def register_pythonizations(space):
    "NOT_RPYTHON"

    allfuncs = [

        ### std::string
        stdstring_c_str,

    ]

    for f in allfuncs:
        _pythonizations[f.__name__] = space.wrap(interp2app(f))

def _method_alias(space, w_pycppclass, m1, m2):
    space.setattr(w_pycppclass, space.wrap(m1),
                  space.getattr(w_pycppclass, space.wrap(m2)))

def pythonize(space, name, w_pycppclass):
    if name == "string":
        space.setattr(w_pycppclass, space.wrap("c_str"), _pythonizations["stdstring_c_str"])
        _method_alias(space, w_pycppclass, "_cppyy_as_builtin", "c_str")
        _method_alias(space, w_pycppclass, "__str__",           "c_str")
