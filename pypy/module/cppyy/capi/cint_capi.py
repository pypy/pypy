import py, os

from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.lltypesystem import rffi
from pypy.rlib import rdynload

__all__ = ['eci', 'c_load_dictionary']

pkgpath = py.path.local(__file__).dirpath().join(os.pardir)
srcpath = pkgpath.join("src")
incpath = pkgpath.join("include")

if os.environ.get("ROOTSYS"):
    rootincpath = [os.path.join(os.environ["ROOTSYS"], "include")]
    rootlibpath = [os.path.join(os.environ["ROOTSYS"], "lib")]
else:
    rootincpath = []
    rootlibpath = []

# force loading in global mode of core libraries, rather than linking with
# them as PyPy uses various version of dlopen in various places; note that
# this isn't going to fly on Windows (note that locking them in objects and
# calling dlclose in __del__ seems to come too late, so this'll do for now)
with rffi.scoped_str2charp('libCint.so') as ll_libname:
    _cintdll = rdynload.dlopen(ll_libname, rdynload.RTLD_GLOBAL | rdynload.RTLD_NOW)
with rffi.scoped_str2charp('libCore.so') as ll_libname:
    _coredll = rdynload.dlopen(ll_libname, rdynload.RTLD_GLOBAL | rdynload.RTLD_NOW)

eci = ExternalCompilationInfo(
    separate_module_files=[srcpath.join("cintcwrapper.cxx")],
    include_dirs=[incpath] + rootincpath,
    includes=["cintcwrapper.h"],
    library_dirs=rootlibpath,
    use_cpp_linker=True,
)

c_load_dictionary = rffi.llexternal(
    "cppyy_load_dictionary",
    [rffi.CCHARP], rdynload.DLLHANDLE,
    compilation_info=eci)
