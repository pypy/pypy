from rpython.jit.backend.llsupport.llmodel import AbstractLLCPU
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.translator.tool.cbuild import ExternalCompilationInfo

class LLVM_CPU(AbstractLLCPU):
    def __init__(self, rtyper, stats, opts=None, translate_support_code=False, gcdescr=None):
        AbstractLLCPU.__init__(self, rtyper, stats, opts, translate_support_code, gcdescr)
        self.define_types()
        self.initialise_api()
        self.Context = self.CreateContext(None)
        module_name = rffi.str2constcharp("hot_code")
        self.Module = self.CreateModule(module_name)
        self.Builder = self.CreateBuilder(None)

    def compile_loop(self, inputargs, operations, looptoken, jd_id =0, unique_id=0, log=True, name='', logger=None):
        arg_types = []
        args = []
        print(inputargs[0])
        print(dir(inputargs[0]))
        for arg in inputargs:
            typ, ref = self.get_llvm_type(arg)
            arg_types.append(typ)
            args.append(ref) #store associated LLVM types and LLVM value refs for each input argument

        signature = self.FunctionType(self.IntType(32), arg_types, len(arg_types), 0)
        trace = self.AddFunction(self.Module, "trace", signature)
        entry = self.AppendBasicBlock(trace, "entry")
        self.PositionBuilderAtEnd(self.Builder, entry)

        #for op in operations:

        i1 = self.BuildAdd(self.Builder, args[0], self.ConstInt(self.IntType(32), 1, 1), "i1")
        self.BuildRet(self.Builder, i1)

    #def compile_to_object(self):
    #    if not self.InitializeNativeTarget():
    #        raise Exception #TODO specify exception type
    #    if not self.InitializeNativeAsmPrinter():
    #        raise Exception
    #    self.SetModuleDataLayout #??

    def setup_once(self):
        pass


    def get_llvm_type(self, val):
        if val.datatype == 'i':
            int_type = self.IntType(32) #TODO: make word size platform independant
            if val.signed == True:
                return (int_type, self.ConstInt(int_type, val.getvalue(), 1))
            else:
                return (int_type, self.ConstInt(int_type, val.getvalue(), 0))
        else:
            return (0,0) #get the syntax checker to shut up

    def initialise_api(self):
        llvm_c = ["llvm-c/"+i for i in ["Core","ExecutionEngine","Target","Analysis"]]
        cflags = ["-I/usr/lib/llvm/11/include  -D_GNU_SOURCE -D__STDC_CONSTANT_MACROS -D__STDC_FORMAT_MACROS -D__STDC_LIMIT_MACROS"]
        info = ExternalCompilationInfo(includes=llvm_c, libraries=["LLVM-11"], include_dirs=["/usr/lib/llvm/11/lib64"], compile_extra=cflags, link_extra=cflags) #TODO: make this platform independant (rather than hardcoding the output of llvm-config for my system)

        self.CreateContext = rffi.llexternal("LLVMContextCreate", [self.Void], self.ContextRef, compilation_info=info)
        self.CreateModule = rffi.llexternal("LLVMModuleCreateWithName", [self.Str], self.ModuleRef, compilation_info=info)
        self.FunctionType = rffi.llexternal("LLVMFunctionType", [self.TypeRef, self.TypeRefPtr, lltype.Unsigned, self.Bool], self.TypeRef, compilation_info=info)
        self.AddFunction = rffi.llexternal("LLVMAddFunction", [self.ModuleRef, self.Str, self.TypeRef], self.ValueRef, compilation_info=info)
        self.AppendBasicBlock = rffi.llexternal("LLVMAppendBasicBlock", [self.ValueRef, self.Str], self.BasicBlockRef, compilation_info=info)
        self.CreateBuilder = rffi.llexternal("LLVMCreateBuilder", [self.Void], self.BuilderRef, compilation_info=info)
        self.PositionBuilderAtEnd = rffi.llexternal("LLVMPositionBuilderAtEnd", [self.BuilderRef, self.BasicBlockRef], self.Void, compilation_info=info)
        self.BuildAdd = rffi.llexternal("LLVMBuildAdd", [self.BuilderRef, self.ValueRef, self.ValueRef, self.Str], self.ValueRef, compilation_info=info)
        self.BuildFAdd = rffi.llexternal("LLVMBuildAdd", [self.BuilderRef, self.ValueRef, self.ValueRef, self.Str], self.ValueRef, compilation_info=info)
        self.BuildRet = rffi.llexternal("LLVMBuildRet", [self.BuilderRef, self.ValueRef], self.ValueRef, compilation_info=info)
        self.GetParam = rffi.llexternal("LLVMGetParam", [self.ValueRef, lltype.Signed], self.ValueRef, compilation_info=info)
        self.Verify = rffi.llexternal("LLVMVerifyModule", [self.ModuleRef, self.VerifierFailureAction, rffi.CCHARPP], self.Bool, compilation_info=info)
        self.DisposeMessage = rffi.llexternal("LLVMDisposeMessage", [self.Str], self.Void, compilation_info=info)
        self.DisposeBuilder = rffi.llexternal("LLVMDisposeBuilder", [self.BuilderRef], self.Void, compilation_info=info)
        self.DiposeModule = rffi.llexternal("LLVMDisposeModule", [self.ModuleRef], self.Void, compilation_info=info)
        self.DisposeContext = rffi.llexternal("LLVMContextDispose", [self.ContextRef], self.Void, compilation_info=info)
        self.IntType = rffi.llexternal("LLVMIntType", [lltype.Unsigned], self.TypeRef, compilation_info=info)
        self.ConstInt = rffi.llexternal("LLVMConstInt", [self.TypeRef, lltype.UnsignedLongLong, self.Bool], self.ValueRef, compilation_info=info)
        self.InitializeNativeTarget = rffi.llexternal("LLVMInitializeNativeTarget", [self.Void], self.Bool, compilation_info=info)
        self.InitializeNativeAsmPrinter = rffi.llexternal("LLVMInitializeNativeTarget", [self.Void], self.Bool, compilation_info=info)
        self.BuildPhi = rffi.llexternal("LLVMBuildPhi", [self.BuilderRef, self.TypeRef, self.Str], self.ValueRef, compilation_info=info)
        self.GetInsertBlock = rffi.llexternal("LLVMGetInsertBlock", [self.BuilderRef], self.BasicBlockRef, compilation_info=info)
        self.PositionBuilderAtEnd = rffi.llexternal("LLVMPositionBuilderAtEnd", [self.BuilderRef, self.BasicBlockRef], self.Void, compilation_info=info)
        self.BuildFCmp = rffi.llexternal("LLVMBuildFCmp", [self.BuilderRef, self.RealPredicate, self.ValueRef, self.ValueRef, self.Str], self.ValueRef, compilation_info=info)
        self.BuildICmp = rffi.llexternal("LLVMBuildICmp", [self.BuilderRef, self.IntPredicate, self.ValueRef, self.ValueRef, self.Str], self.ValueRef, compilation_info=info)
        self.CreateBasicBlock = rffi.llexternal("LLVMCreateBasicBlockInContext", [self.ContextRef, self.Str], self.BasicBlockRef, compilation_info=info)
        self.GetParent = rffi.llexternal("LLVMGetBasicBlockParent", [self.BasicBlockRef], self.ValueRef, compilation_info=info)
        self.AddIncoming = rffi.llexternal("LLVMAddIncoming", [self.ValueRef, self.ValueRefPtr, self.BasicBlockRef, lltype.Unsigned], self.Void, compilation_info=info)
        self.BuildBr = rffi.llexternal("LLVMBuildBr", [self.BuilderRef, self.BasicBlockRef], self.ValueRef, compilation_info=info)
        self.BuildCondBr = rffi.llexternal("LLVMBuildCondBr", [self.BuilderRef, self.ValueRef, self.BasicBlockRef, self.BasicBlockRef], self.ValueRef, compilation_info=info)


    def define_types(self):
        """
        LLVM uses polymorphic types which C can't represent, so LLVM-C doesn't define them with concrete/primitive types,
        as such we have to refer to most of them with void pointers, but as the LLVM API also manages memory deallocation for us this is likely the simplest choice anyway.
        """
        self.Void = lltype.Void
        self.VoidPtr = rffi.VOIDP
        self.VoidPtrPtr = rffi.VOIDPP
        self.Enum = lltype.Unsigned
        self.ModuleRef = self.VoidPtr
        self.TypeRef = self.VoidPtr
        self.TypeRefPtr = self.VoidPtrPtr
        self.ContextRef = self.VoidPtr
        self.ValueRef = self.VoidPtr
        self.ValueRefPtr = self.VoidPtrPtr
        self.GenericValueRef = self.VoidPtr
        self.BasicBlockRef = self.VoidPtr
        self.BuilderRef = self.VoidPtr
        self.Bool = lltype.Signed #LLVMBOOL is typedefed to int32
        self.Str = rffi.CONST_CCHARP
        self.VerifierFailureAction = self.Enum
        self.RealPredicate = self.Enum
        self.IntPredicate = self.Enum
