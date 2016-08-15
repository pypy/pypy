import py, os

from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.lltypesystem import rffi
from rpython.rlib import libffi, rdynload

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


# Cling-specific pythonizations
def register_pythonizations(space):
    "NOT_RPYTHON"
    pass

def _method_alias(space, w_pycppclass, m1, m2):
    space.setattr(w_pycppclass, space.wrap(m1),
                  space.getattr(w_pycppclass, space.wrap(m2)))

def pythonize(space, name, w_pycppclass):
    if name == "string":
        _method_alias(space, w_pycppclass, "_cppyy_as_builtin", "c_str")
