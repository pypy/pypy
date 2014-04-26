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
                       os.path.join(os.environ["ROOTSYS"], "interpreter/llvm/inst/include")]
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

eci = ExternalCompilationInfo(
    separate_module_files=[srcpath.join("clingcwrapper.cxx")],
    include_dirs=[incpath] + rootincpath,
    includes=["clingcwrapper.h"],
    library_dirs=rootlibpath,
    libraries=["Cling"],
    compile_extra=["-fno-strict-aliasing"],
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

def pythonize(space, name, w_pycppclass):
    pass
