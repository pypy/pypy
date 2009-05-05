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
cppname = os.path.join(os.path.dirname(__file__), 'demo2.cpp')

if (not os.path.isfile(libname) or
        os.path.getmtime(cname) > os.path.getmtime(libname) or
        os.path.getmtime(cppname) > os.path.getmtime(libname)):
    if not os.path.isdir(dirname):
        if not os.path.isdir(cachename):
            os.mkdir(cachename)
        os.mkdir(dirname)

    def do(cmdline):
        log(cmdline)
        err = os.system(cmdline)
        if err:
            raise Exception("gcc command failed")

    o1name = os.path.join(dirname, 'demo1.o')
    o2name = os.path.join(dirname, 'demo2.o')
    do("gcc -c '%s' -o '%s' -I/home/fijal/load/llvm/include" % (cname, o1name))
    do("g++ -c '%s' -o '%s' `%s --cppflags`" % (cppname, o2name, llvm_config))
    do("g++ -shared '%s' '%s' -o '%s' " % (o1name, o2name, libname) +
       " `%s --cflags --ldflags --libs jit engine` -lLLVMInstrumentation -lLLVMipo -lLLVMipa -lLLVMTransformUtils -lLLVMAnalysis -lLLVMCore" % llvm_config)

compilation_info = ExternalCompilationInfo(
    library_dirs = [dirname],
    libraries    = ['pypy_cache_llvm'],
)

# ____________________________________________________________

Debug = True

def llexternal(name, args, result, **kwds):
    ll = rffi.llexternal(name, args, result,
                         compilation_info=compilation_info,
                         **kwds)
    if Debug:
        def func(*args):
            print name
            res = ll(*args)
            print '\t->', res
            return res
        return func
    else:
        return ll

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

class Predicate:
    EQ = 32      # equal
    NE = 33      # not equal
    UGT = 34     # unsigned greater than
    UGE = 35     # unsigned greater or equal
    ULT = 36     # unsigned less than
    ULE = 37     # unsigned less or equal
    SGT = 38     # signed greater than
    SGE = 39     # signed greater or equal
    SLT = 40     # signed less than
    SLE = 41     # signed less or equal

class CallConv:
    C           = 0
    Fast        = 8
    Cold        = 9
    X86Stdcall  = 64
    X86Fastcall = 65

# ____________________________________________________________

LLVMDisposeMessage = llexternal('LLVMDisposeMessage', [rffi.CCHARP],
                                lltype.Void)

LLVMModuleCreateWithName = llexternal('LLVMModuleCreateWithName',
                                      [rffi.CCHARP],
                                      LLVMModuleRef)
LLVMDumpModule = llexternal('LLVMDumpModule', [LLVMModuleRef], lltype.Void)

LLVMInt1Type = llexternal('LLVMInt1Type', [], LLVMTypeRef)
LLVMInt8Type = llexternal('LLVMInt8Type', [], LLVMTypeRef)
LLVMInt32Type = llexternal('LLVMInt32Type', [], LLVMTypeRef)
LLVMInt64Type = llexternal('LLVMInt64Type', [], LLVMTypeRef)
LLVMFunctionType = llexternal('LLVMFunctionType',
                              [LLVMTypeRef,                 # return type
                               rffi.CArrayPtr(LLVMTypeRef), # param types
                               rffi.UINT,                   # param count
                               rffi.INT],                   # flag: is_vararg
                              LLVMTypeRef)
LLVMPointerType = llexternal('LLVMPointerType', [LLVMTypeRef,  # element type
                                                 rffi.UINT],   # address space
                             LLVMTypeRef)

LLVMTypeOf = llexternal('LLVMTypeOf', [LLVMValueRef], LLVMTypeRef)
LLVMConstInt = llexternal('LLVMConstInt', [LLVMTypeRef,     # type
                                           rffi.ULONGLONG,  # value
                                           rffi.INT],       # flag: is_signed
                          LLVMValueRef)
LLVMConstIntToPtr = llexternal('LLVMConstIntToPtr',
                               [LLVMValueRef,         # constant integer value
                                LLVMTypeRef],         # type of the result
                               LLVMValueRef)

LLVMAddFunction = llexternal('LLVMAddFunction',
                             [LLVMModuleRef,                # module
                              rffi.CCHARP,                  # name
                              LLVMTypeRef],                 # function type
                             LLVMValueRef)
LLVMSetFunctionCallConv = llexternal('LLVMSetFunctionCallConv',
                                     [LLVMValueRef,         # function
                                      rffi.UINT],           # new call conv
                                     lltype.Void)
LLVMGetParam = llexternal('LLVMGetParam',
                          [LLVMValueRef,                    # function
                           rffi.UINT],                      # index
                          LLVMValueRef)

LLVMAppendBasicBlock = llexternal('LLVMAppendBasicBlock',
                                  [LLVMValueRef,            # function
                                   rffi.CCHARP],            # name
                                  LLVMBasicBlockRef)

LLVMSetInstructionCallConv = llexternal('LLVMSetInstructionCallConv',
                                        [LLVMValueRef,   # call instruction
                                         rffi.UINT],     # new call conv
                                        lltype.Void)
LLVMSetTailCall = llexternal('LLVMSetTailCall',
                             [LLVMValueRef,        # call instruction
                              rffi.INT],           # flag: is_tail
                             lltype.Void)
LLVMAddIncoming = llexternal('LLVMAddIncoming',
                             [LLVMValueRef,                 # phi node
                              rffi.CArrayPtr(LLVMValueRef), # incoming values
                              rffi.CArrayPtr(LLVMBasicBlockRef), # incom.blocks
                              rffi.UINT],                   # count
                             lltype.Void)
LLVMCreateBuilder = llexternal('LLVMCreateBuilder', [], LLVMBuilderRef)
LLVMPositionBuilderAtEnd = llexternal('LLVMPositionBuilderAtEnd',
                                      [LLVMBuilderRef,      # builder
                                       LLVMBasicBlockRef],  # block
                                      lltype.Void)
LLVMGetInsertBlock = llexternal('LLVMGetInsertBlock', [LLVMBuilderRef],
                                LLVMBasicBlockRef)
LLVMDisposeBuilder = llexternal('LLVMDisposeBuilder', [LLVMBuilderRef],
                                lltype.Void)

LLVMBuildRet = llexternal('LLVMBuildRet', [LLVMBuilderRef,  # builder,
                                           LLVMValueRef],   # result
                          LLVMValueRef)
LLVMBuildBr = llexternal('LLVMBuildBr', [LLVMBuilderRef,    # builder,
                                         LLVMBasicBlockRef],# destination block
                         LLVMValueRef)
LLVMBuildCondBr = llexternal('LLVMBuildCondBr',
                             [LLVMBuilderRef,      # builder
                              LLVMValueRef,        # condition
                              LLVMBasicBlockRef,   # block if true
                              LLVMBasicBlockRef],  # block if false
                             LLVMValueRef)

for _name in ['Add', 'Sub', 'LShr']:
    globals()['LLVMBuild' + _name] = llexternal('LLVMBuild' + _name,
        [LLVMBuilderRef,  # builder
         LLVMValueRef,    # left-hand side
         LLVMValueRef,    # right-hand side
         rffi.CCHARP],    # name of result
        LLVMValueRef)

for _name in ['Neg', 'Not']:
    globals()['LLVMBuild' + _name] = llexternal('LLVMBuild' + _name,
        [LLVMBuilderRef,  # builder
         LLVMValueRef,    # argument
         rffi.CCHARP],    # name of result
        LLVMValueRef)

LLVMBuildLoad = llexternal('LLVMBuildLoad',
                           [LLVMBuilderRef,     # builder
                            LLVMValueRef,       # pointer location
                            rffi.CCHARP],       # name of result
                           LLVMValueRef)
LLVMBuildStore = llexternal('LLVMBuildStore',
                            [LLVMBuilderRef,    # builder
                             LLVMValueRef,      # value
                             LLVMValueRef],     # pointer location
                            LLVMValueRef)
LLVMBuildTrunc = llexternal('LLVMBuildTrunc',
                            [LLVMBuilderRef,    # builder
                             LLVMValueRef,      # value
                             LLVMTypeRef,       # destination type
                             rffi.CCHARP],      # name of result
                            LLVMValueRef)
LLVMBuildZExt = llexternal('LLVMBuildZExt',
                           [LLVMBuilderRef,    # builder
                            LLVMValueRef,      # value
                            LLVMTypeRef,       # destination type
                            rffi.CCHARP],      # name of result
                           LLVMValueRef)
LLVMBuildBitCast = llexternal('LLVMBuildBitCast',
                              [LLVMBuilderRef, # builder
                               LLVMValueRef,   # value
                               LLVMTypeRef,    # destination type
                               rffi.CCHARP],   # name of result
                              LLVMValueRef)
LLVMBuildICmp = llexternal('LLVMBuildICmp',
                           [LLVMBuilderRef,  # builder
                            rffi.INT,        # predicate (see LLVMIntPredicate)
                            LLVMValueRef,    # left-hand side
                            LLVMValueRef,    # right-hand side
                            rffi.CCHARP],    # name of result
                           LLVMValueRef)
LLVMBuildPhi = llexternal('LLVMBuildPhi',
                          [LLVMBuilderRef,   # builder
                           LLVMTypeRef,      # type of value
                           rffi.CCHARP],     # name of result
                          LLVMValueRef)
LLVMBuildCall = llexternal('LLVMBuildCall',
                           [LLVMBuilderRef,               # builder
                            LLVMValueRef,                 # function
                            rffi.CArrayPtr(LLVMValueRef), # arguments
                            rffi.UINT,                    # argument count
                            rffi.CCHARP],                 # name of result
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
LLVMDisposeGenericValue = llexternal('LLVMDisposeGenericValue',
                                     [LLVMGenericValueRef], lltype.Void)

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
LLVMDisposeExecutionEngine = llexternal('LLVMDisposeExecutionEngine',
                                        [LLVMExecutionEngineRef],
                                        lltype.Void)

LLVMRunFunction = llexternal('LLVMRunFunction',
                             [LLVMExecutionEngineRef,
                              LLVMValueRef,                         # function
                              rffi.UINT,                            # num args
                              rffi.CArrayPtr(LLVMGenericValueRef)], # args
                             LLVMGenericValueRef)   # return value

LLVM_SetFlags = llexternal('_LLVM_SetFlags', [], lltype.Void)
LLVM_EE_Create = llexternal('_LLVM_EE_Create', [LLVMModuleRef],
                            LLVMExecutionEngineRef)
LLVM_EE_getPointerToFunction = llexternal('_LLVM_EE_getPointerToFunction',
                                          [LLVMExecutionEngineRef,
                                           LLVMValueRef],           # function
                                          rffi.VOIDP)
