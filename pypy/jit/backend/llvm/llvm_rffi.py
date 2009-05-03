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
       " `%s --cflags --ldflags --libs jit engine`" % llvm_config)

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

LLVMModuleRef = opaqueptr('struct LLVMOpaqueModule')
LLVMTypeRef = opaqueptr('struct LLVMOpaqueType')
LLVMValueRef = opaqueptr('struct LLVMOpaqueValue')
LLVMBasicBlockRef = opaqueptr('struct LLVMOpaqueBasicBlock')
LLVMBuilderRef = opaqueptr('struct LLVMOpaqueBuilder')
LLVMModuleProviderRef = opaqueptr('struct LLVMOpaqueModuleProvider')
LLVMGenericValueRef = opaqueptr('struct LLVMOpaqueGenericValue')
LLVMExecutionEngineRef = opaqueptr('struct LLVMOpaqueExecutionEngine')

# ____________________________________________________________

LLVMModuleCreateWithName = llexternal('LLVMModuleCreateWithName',
                                      [rffi.CCHARP],
                                      LLVMModuleRef)
LLVMDumpModule = llexternal('LLVMDumpModule', [LLVMModuleRef], lltype.Void)

LLVMInt32Type = llexternal('LLVMInt32Type', [], LLVMTypeRef)
LLVMFunctionType = llexternal('LLVMFunctionType',
                              [LLVMTypeRef,                 # return type
                               rffi.CArrayPtr(LLVMTypeRef), # param types
                               rffi.UINT,                   # param count
                               rffi.INT],                   # flag: is vararg
                              LLVMTypeRef)

LLVMAddFunction = llexternal('LLVMAddFunction',
                             [LLVMModuleRef,                # module
                              rffi.CCHARP,                  # name
                              LLVMTypeRef],                 # function type
                             LLVMValueRef)
LLVMGetParam = llexternal('LLVMGetParam',
                          [LLVMValueRef,                    # function
                           rffi.UINT],                      # index
                          LLVMValueRef)

LLVMAppendBasicBlock = llexternal('LLVMAppendBasicBlock',
                                  [LLVMValueRef,            # function
                                   rffi.CCHARP],            # name
                                  LLVMBasicBlockRef)

LLVMCreateBuilder = llexternal('LLVMCreateBuilder', [], LLVMBuilderRef)
LLVMPositionBuilderAtEnd = llexternal('LLVMPositionBuilderAtEnd',
                                      [LLVMBuilderRef,      # builder
                                       LLVMBasicBlockRef],  # block
                                      lltype.Void)

LLVMBuildRet = llexternal('LLVMBuildRet', [LLVMBuilderRef,  # builder,
                                           LLVMValueRef],   # result
                          LLVMValueRef)
LLVMBuildAdd = llexternal('LLVMBuildAdd', [LLVMBuilderRef,  # builder
                                           LLVMValueRef,    # left-hand side
                                           LLVMValueRef,    # right-hand side
                                           rffi.CCHARP],    # name of result
                          LLVMValueRef)

LLVMCreateModuleProviderForExistingModule = llexternal(
    'LLVMCreateModuleProviderForExistingModule', [LLVMModuleRef],
    LLVMModuleProviderRef)

# ____________________________________________________________

LLVMCreateGenericValueOfInt = llexternal('LLVMCreateGenericValueOfInt',
                                         [LLVMTypeRef,      # type
                                          rffi.ULONGLONG,   # value
                                          rffi.INT],        # flag: is_signed
                                         LLVMGenericValueRef)

LLVMGenericValueToInt = llexternal('LLVMGenericValueToInt',
                                   [LLVMGenericValueRef,
                                    rffi.INT],              # flag: is_signed
                                   rffi.ULONGLONG)

LLVMCreateJITCompiler = llexternal('LLVMCreateJITCompiler',
                                   [rffi.CArrayPtr(LLVMExecutionEngineRef),
                                    LLVMModuleProviderRef,
                                    rffi.INT,                      # "fast"
                                    rffi.CArrayPtr(rffi.CCHARP)],  # -> error
                                   rffi.INT)

LLVMRunFunction = llexternal('LLVMRunFunction',
                             [LLVMExecutionEngineRef,
                              LLVMValueRef,                         # function
                              rffi.UINT,                            # num args
                              rffi.CArrayPtr(LLVMGenericValueRef)], # args
                             LLVMGenericValueRef)   # return value
