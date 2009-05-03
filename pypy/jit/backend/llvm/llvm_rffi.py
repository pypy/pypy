import py, os, sys
import pypy
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo, log

if sys.platform != 'linux2':
    py.test.skip("Linux only for now")

# ____________________________________________________________

llvm_config = 'llvm-config'
cachename = os.path.join(os.path.dirname(pypy.__file__), '_cache')
dirname = os.path.join(cachename, 'libs')
libname = os.path.join(dirname, 'pypy_cache_llvm.so')
cname = os.path.join(os.path.dirname(__file__), 'demo1.c')

if not os.path.isfile(libname) or (os.path.getmtime(cname) >
                                   os.path.getmtime(libname)):
    if not os.path.isdir(dirname):
        if not os.path.isdir(cachename):
            os.mkdir(cachename)
        os.mkdir(dirname)

    def do(cmdline):
        log(cmdline)
        err = os.system(cmdline)
        if err:
            raise Exception("gcc command failed")

    oname = os.path.join(dirname, 'demo1.o')
    do("gcc -c '%s' -o '%s'" % (cname, oname))
    do("g++ -shared '%s' -o '%s'" % (oname, libname) +
       " `%s --libs jit`" % llvm_config +
       " `%s --cflags`" % llvm_config +
       " `%s --ldflags`" % llvm_config +
       "")

compilation_info = ExternalCompilationInfo(
    library_dirs = [dirname],
    libraries    = ['pypy_cache_llvm'],
)

# ____________________________________________________________

def llexternal(name, args, result, **kwds):
    return rffi.llexternal(name, args, result,
                           compilation_info=compilation_info,
                           **kwds)

def opaqueptr(name):
    return rffi.VOIDP  # lltype.Ptr(rffi.COpaque(name))

LLVMModuleRef = opaqueptr('struct LLVMModuleOpaque')

LLVMModuleCreateWithName = llexternal('LLVMModuleCreateWithName',
                                      [rffi.CCHARP],
                                      LLVMModuleRef)
