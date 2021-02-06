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

        self.CreateModule = rffi.llexternal("LLVMModuleCreateWithName", [self.Str], self.ModuleRef, compilation_info=info)
        self.FunctionType = rffi.llexternal("LLVMFunctionType", [self.TypeRef, lltype.Ptr(self.TypeRef), lltype.Unsigned, self.Bool], self.TypeRef, compilation_info=info)
        self.AddFunction = rffi.llexternal("LLVMAddFunction", [self.ModuleRef, self.Str, self.TypeRef], self.ValueRef, compilation_info=info)
        self.AppendBasicBlock = rffi.llexternal("LLVMAppendBasicBlock", [self.ValueRef, self.Str], self.BasicBlockRef, compilation_info=info)
        self.CreateBuilder = rffi.llexternal("LLVMCreateBuilder", self.Void, self.BuilderRef, compilation_info=info)
        self.PositionBuilderAtEnd = rffi.llexternal("LLVMPositionBuilderAtEnd", [self.BuilderRef, self.BasicBlockRef], self.Void, compilation_info=info)
        self.BuildAdd = rffi.llexternal("LLVMBuildAdd", [self.BuilderRef, self.ValueRef, self.ValueRef, self.Str], self.ValueRef, compilation_info=info)
        self.BuildRet = rffi.llexternal("LLVMBuildRet", [self.BuilderRef, self.ValueRef], self.ValueRef, compilation_info=info)
        self.GetParam = rffi.llexternal("LLVMGetParam", [self.ValueRef, lltype.Int], self.ValueRef, compilation_info=info)
        self.Verify = rffi.llexternal("LLVMVerifyModule", [self.ModuleRef, self.VerifierFailureAction, lltype.Ptr(lltype.Ptr(lltype.Char))], self.Bool, compilation_info=info)
        self.DisposeMessage = rffi.llexternal("LLVMDisposeMessage", [lltype.Ptr(lltype.Char)], self.Void, compilation_info=info)
        self.DisposeBuilder = rffi.llexternal("LLVMDisposeBuilder", [self.BuilderRef], self.Void, compilation_info=info)
        self.DiposeModule = rffi.llexternal("LLVMDisposeModule", [self.ModuleRef], self.Void, compilation_info=info)

    def set_types(self):
        """
        LLVM uses polymorphic types which C can't represent, so LLVM-C doesn't define them with concrete/primitive types,
        as such we have to refer to most of them with void pointers, but as the LLVM API also manages memory deallocation for us this is likely the simplest choice anyway.
        """
        self.Void = lltype.Void
        self.VoidPtr = lltype.Ptr(lltype.Void)
        self.ModuleRef = self.VoidPtr
        self.TypeRef = self.VoidPtr
        self.ContextRef = self.VoidPtr
        self.ValueRef = self.VoidPtr
        self.BasicBlockRef = self.VoidPtr
        self.BuilderRef = self.VoidPtr
        self.Bool = lltype.Int
        self.Str = lltype.ConstPtr(lltype.Char)
        self.VerifierFailureAction = lltype.Unsigned
