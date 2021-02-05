from rpython.jit.backend.llsupport.llmodel import AbstractLLCPU
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.translator.tool.cbuild import ExternalCompilationInfo

class LLVM_CPU(AbstractLLCPU):
    def __init__(self, rtyper, stats, opts=None, translate_support_code=False, gcdescr=None):
        AbstractLLCPU.__init__(self, rtyper, stats, opts, translate_support_code, gcdescr)

    def initialise_api(self):
        llvm_c = ["llvm-c/"+i for i in ["Core","ExecutionEngine","Target","Analysis","BitWriter"]]
        cflags = "-I/usr/lib/llvm/11/include  -D_GNU_SOURCE -D__STDC_CONSTANT_MACROS -D__STDC_FORMAT_MACROS -D__STDC_LIMIT_MACROS"
        info = ExternalCompilationInfo(includes=llvm_c, libraries="LLVM-11", include_dirs="/usr/lib/llvm/11/lib64", compile_extra=cflags, link_extra=cflags) #TODO: make this platform independant (rather than hardcoding the output of llvm-config for my system)

        self.LLVMModuleCreateWithName = rffi.llexternal("LLVMModuleCreateWithName", lltype.Ptr(lltype.Char), self.LLVMModuleRef, compilation_info=info)

    def set_types(self): #LLVM uses polymorphic types which C can't represent, so LLVM-C doesn't define them with concrete/primitive types. As such we have to refer to them all with void pointers, but as the LLVM API also manages memory deallocation for us this is likely the simplest choice anyway.
        self.LLVMModuleRef = lltype.Ptr(lltype.Void)
        self.LLVMTypeRef = lltype.Ptr(lltype.Void)
        self.LLVMContextRef = lltype.Ptr(lltype.Void)
        self.LLVMValueRef = lltype.Ptr(lltype.Void)
        self.LLVMBasicBlockRef = lltype.Ptr(lltype.Void)
        self.LLVMBuilderRef = lltype.Ptr(lltype.Void)
