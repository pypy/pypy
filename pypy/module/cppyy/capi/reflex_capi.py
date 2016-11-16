import py, os

from rpython.rlib import libffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo

__all__ = ['identify', 'std_string_name', 'eci', 'c_load_dictionary']

pkgpath = py.path.local(__file__).dirpath().join(os.pardir)
srcpath = pkgpath.join("src")
incpath = pkgpath.join("include")

# require local translator path to pickup common defs
from rpython.translator import cdir
translator_c_dir = py.path.local(cdir)

import commands
(config_stat, incdir) = commands.getstatusoutput("root-config --incdir")

if os.environ.get("ROOTSYS"):
    if config_stat != 0:     # presumably Reflex-only
        rootincpath = [os.path.join(os.environ["ROOTSYS"], "include")]
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
    return 'Reflex'

ts_reflect = False
ts_call    = 'auto'
ts_memory  = 'auto'
ts_helper  = 'auto'

std_string_name = 'std::basic_string<char>'

eci = ExternalCompilationInfo(
    separate_module_files=[srcpath.join("reflexcwrapper.cxx")],
    include_dirs=[incpath, translator_c_dir] + rootincpath,
    includes=["reflexcwrapper.h"],
    library_dirs=rootlibpath,
    libraries=["Reflex"],
    use_cpp_linker=True,
)

def c_load_dictionary(name):
    return libffi.CDLL(name)


# Reflex-specific pythonizations
def register_pythonizations(space):
    "NOT_RPYTHON"
    pass

def pythonize(space, name, w_pycppclass):
    pass
