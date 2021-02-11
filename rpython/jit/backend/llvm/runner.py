from rpython.jit.backend.llsupport.llmodel import AbstractLLCPU
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rtyper.lltypesystem.rffi import str2constcharp
from rpython.translator.tool.cbuild import ExternalCompilationInfo

class LLVM_CPU(AbstractLLCPU):
    def __init__(self, rtyper, stats, opts=None,
                 translate_support_code=False, gcdescr=None):
        AbstractLLCPU.__init__(self, rtyper, stats, opts,
                               translate_support_code, gcdescr)

        self.define_types()
        self.initialise_api()

        if self.InitializeNativeTarget(None): #returns 0 on success
            raise Exception #TODO: specify exception type
        if self.InitializeNativeAsmPrinter(None):
            raise Exception
        if self.InitializeNativeAsmParser(None):
            raise Exception

        self.Context = self.CreateContext(None)
        self.Module = self.CreateModule(str2constcharp("hot_code"))
        self.Builder = self.CreateBuilder(None)
        data_layout = self.CreateTargetData(str2constcharp(
            "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128")) #TODO: make platform independant
        self.SetModuleDataLayout(self.Module, data_layout)


    def compile_loop(self, inputargs, operations, looptoken, jd_id=0,
                     unique_id=0, log=True, name='', logger=None):

        arg_types, args = self.convert_args(inputargs) #store associated LLVM types and LLVM value refs for each input argument

        signature = self.FunctionType(self.IntType(32),
                                      arg_types,
                                      len(inputargs), 0)
        trace = self.AddFunction(self.Module,
                                 str2constcharp("trace"),
                                 signature)
        entry = self.AppendBasicBlock(trace, str2constcharp("entry"))
        self.PositionBuilderAtEnd(self.Builder, entry)

        #this is where an opcode dispatch loop will go
        i1 = self.BuildAdd(self.Builder, args[0],
                           self.ConstInt(self.IntType(32), 1, 1),
                           str2constcharp("i1"))
        self.BuildRet(self.Builder, i1)

        looptoken.compiled_loop_token = self.compile_to_obj()
        lltype.free(arg_types, flavor='raw') #TODO: check if safe if using LLVM's JIT

    def compile_to_obj(self):
        pass

    def setup_once(self):
        pass

    def convert_args(self, inputargs):
        arg_array = rffi.CArray(self.TypeRef) #TODO: look into if missing out on optimisations by not using fixed array
        arg_types_ptr = lltype.malloc(arg_array, n=len(inputargs), flavor='raw')
        arg_types = arg_types_ptr._getobj()

        args = []
        for c, arg in enumerate(inputargs):
            typ, ref = self.get_input_llvm_type(arg)
            arg_types.setitem(c, typ)
            args.append(ref)
        return (arg_types_ptr, args)

    def get_input_llvm_type(self, val):
        if val.datatype == 'i':
            int_type = self.IntType(val.bytesize)
            if val.signed == True:
                return (int_type, self.ConstInt(int_type, val.getvalue(), 1))
            else:
                return (int_type, self.ConstInt(int_type, val.getvalue(), 0))

    def initialise_api(self):
        header_files = ["Core","ExecutionEngine","Target","Analysis","BitWriter",
                        "DataTypes","BitReader","Comdat","DebugInfo",
                        "Disassembler","DisassemblerTypes","Error","ErrorHandling",
                        "ExternC","IRReader","Initialization","LinkTimeOptimizer",
                        "Linker","Object","Orc","OrcBindings","Remarks",
                        "Support","TargetMachine","Types"]
        llvm_c = ["llvm-c/"+f+".h" for f in header_files]
        cflags = ["""-I/usr/lib/llvm/11/include -D_GNU_SOURCE
                    -D__STDC_CONSTANT_MACROS -D__STDC_FORMAT_MACROS
                    -D__STDC_LIMIT_MACROS"""] #know this should be in the includes arg, but llvm is weird and only works this way (by my testing anyway)
        path = "/home/muke/Programming/Project/pypy/rpython/jit/backend/llvm/llvm_wrapper/" #TODO: get real path
        info = ExternalCompilationInfo(includes=llvm_c+[path+"wrapper.h"],
                                       libraries=["LLVM-11","wrapper"],
                                       include_dirs=["/usr/lib/llvm/11/lib64",
                                                     "/usr/lib/llvm/11/include",path],
                                       library_dirs=["/usr/lib/llvm/11/lib64",path],
                                       compile_extra=cflags, link_extra=cflags) #TODO: make this platform independant (rather than hardcoding the output of llvm-config for my system)

        self.GetGlobalPassRegistry = rffi.llexternal("LLVMGetGlobalPassRegistry",
                                                    [self.Void],
                                                     self.PassRegistryRef,
                                                     compilation_info=info)
        self.CreateContext = rffi.llexternal("LLVMContextCreate",
                                             [self.Void], self.ContextRef,
                                             compilation_info=info)
        self.CreateModule = rffi.llexternal("LLVMModuleCreateWithName",
                                            [self.Str], self.ModuleRef,
                                            compilation_info=info)
        self.FunctionType = rffi.llexternal("LLVMFunctionType",
                                            [self.TypeRef, self.TypeRefPtr,
                                             lltype.Unsigned, self.Bool],
                                            self.TypeRef, compilation_info=info)
        self.AddFunction = rffi.llexternal("LLVMAddFunction",
                                           [self.ModuleRef, self.Str, self.TypeRef],
                                           self.ValueRef, compilation_info=info)
        self.AppendBasicBlock = rffi.llexternal("LLVMAppendBasicBlock",
                                                [self.ValueRef, self.Str],
                                                self.BasicBlockRef,
                                                compilation_info=info)
        self.CreateBuilder = rffi.llexternal("LLVMCreateBuilder",
                                             [self.Void], self.BuilderRef,
                                             compilation_info=info)
        self.PositionBuilderAtEnd = rffi.llexternal("LLVMPositionBuilderAtEnd",
                                                    [self.BuilderRef,
                                                     self.BasicBlockRef], self.Void,
                                                    compilation_info=info)
        self.BuildAdd = rffi.llexternal("LLVMBuildAdd",
                                        [self.BuilderRef, self.ValueRef,
                                         self.ValueRef, self.Str],
                                        self.ValueRef, compilation_info=info)
        self.BuildFAdd = rffi.llexternal("LLVMBuildAdd",
                                         [self.BuilderRef, self.ValueRef,
                                          self.ValueRef, self.Str],
                                         self.ValueRef, compilation_info=info)
        self.BuildRet = rffi.llexternal("LLVMBuildRet",
                                        [self.BuilderRef, self.ValueRef],
                                        self.ValueRef, compilation_info=info)
        self.GetParam = rffi.llexternal("LLVMGetParam",
                                        [self.ValueRef, lltype.Signed],
                                        self.ValueRef, compilation_info=info)
        self.Verify = rffi.llexternal("LLVMVerifyModule",
                                      [self.ModuleRef, self.VerifierFailureAction,
                                       rffi.CCHARPP], self.Bool,
                                      compilation_info=info) #FIXME: figure out how to pass a ptr to a null ptr as an object for the error message
        self.DisposeMessage = rffi.llexternal("LLVMDisposeMessage",
                                              [self.Str], self.Void,
                                              compilation_info=info)
        self.DisposeBuilder = rffi.llexternal("LLVMDisposeBuilder",
                                              [self.BuilderRef], self.Void,
                                              compilation_info=info)
        self.DiposeModule = rffi.llexternal("LLVMDisposeModule",
                                            [self.ModuleRef], self.Void,
                                            compilation_info=info)
        self.DisposeContext = rffi.llexternal("LLVMContextDispose",
                                              [self.ContextRef], self.Void,
                                              compilation_info=info)
        self.IntType = rffi.llexternal("LLVMIntType",
                                       [lltype.Unsigned], self.TypeRef,
                                       compilation_info=info)
        self.ConstInt = rffi.llexternal("LLVMConstInt",
                                        [self.TypeRef, lltype.UnsignedLongLong,
                                         self.Bool], self.ValueRef,
                                        compilation_info=info)
        self.InitializeCore = rffi.llexternal("LLVMInitializeCore",
                                              [self.Void], self.Bool,
                                              compilation_info=info)
        self.BuildPhi = rffi.llexternal("LLVMBuildPhi",
                                        [self.BuilderRef, self.TypeRef, self.Str],
                                        self.ValueRef, compilation_info=info)
        self.GetInsertBlock = rffi.llexternal("LLVMGetInsertBlock",
                                              [self.BuilderRef], self.BasicBlockRef,
                                              compilation_info=info)
        self.PositionBuilderAtEnd = rffi.llexternal("LLVMPositionBuilderAtEnd",
                                                    [self.BuilderRef,
                                                     self.BasicBlockRef],
                                                    self.Void, compilation_info=info)
        self.BuildFCmp = rffi.llexternal("LLVMBuildFCmp",
                                         [self.BuilderRef, self.RealPredicate,
                                          self.ValueRef, self.ValueRef,
                                          self.Str], self.ValueRef,
                                          compilation_info=info)
        self.BuildICmp = rffi.llexternal("LLVMBuildICmp",
                                         [self.BuilderRef, self.IntPredicate,
                                          self.ValueRef, self.ValueRef,
                                          self.Str], self.ValueRef,
                                         compilation_info=info)
        self.CreateBasicBlock = rffi.llexternal("LLVMCreateBasicBlockInContext",
                                                [self.ContextRef, self.Str],
                                                self.BasicBlockRef,
                                                compilation_info=info)
        self.GetParent = rffi.llexternal("LLVMGetBasicBlockParent",
                                         [self.BasicBlockRef], self.ValueRef,
                                         compilation_info=info)
        self.AddIncoming = rffi.llexternal("LLVMAddIncoming",
                                           [self.ValueRef, self.ValueRefPtr,
                                            self.BasicBlockRef,lltype.Unsigned],
                                           self.Void, compilation_info=info)
        self.BuildBr = rffi.llexternal("LLVMBuildBr",
                                       [self.BuilderRef, self.BasicBlockRef],
                                       self.ValueRef, compilation_info=info)
        self.BuildCondBr = rffi.llexternal("LLVMBuildCondBr",
                                           [self.BuilderRef, self.ValueRef,
                                            self.BasicBlockRef, self.BasicBlockRef],
                                           self.ValueRef, compilation_info=info)
        self.GetDataLayout = rffi.llexternal("LLVMGetDataLayoutStr",
                                             [self.ModuleRef], self.Str,
                                             compilation_info=info)
        self.SetModuleDataLayout = rffi.llexternal("LLVMSetModuleDataLayout",
                                                   [self.ModuleRef,
                                                    self.TargetDataRef],
                                                   self.Void, compilation_info=info)
        self.CreateTargetData = rffi.llexternal("LLVMCreateTargetData",
                                                [self.Str], self.TargetDataRef,
                                                compilation_info=info)
        self.InitializeNativeTarget = rffi.llexternal("InitializeNativeTarget",
                                                      [self.Void], self.Bool,
                                                      compilation_info=info) #following three functions are from our own libwrapper.so
        self.InitializeNativeAsmPrinter = rffi.llexternal("InitializeNativeAsmPrinter",
                                                          [self.Void], self.Bool,
                                                          compilation_info=info)
        self.InitializeNativeAsmParser = rffi.llexternal("InitializeNativeAsmParser",
                                                         [self.Void], self.Bool,
                                                         compilation_info=info)


    def define_types(self):
        """
        LLVM uses polymorphic types which C can't represent,
        so LLVM-C doesn't define them with concrete/primitive types.
        As such we have to refer to most of them with void pointers,
        but as the LLVM API also manages memory deallocation for us,
        this is likely the simplest choice anyway.
        """
        self.Void = lltype.Void
        self.VoidPtr = rffi.VOIDP
        self.VoidPtrPtr = rffi.VOIDPP
        self.Enum = lltype.Unsigned
        self.PassRegistryRef = self.VoidPtr
        self.ModuleRef = self.VoidPtr
        self.TypeRef = self.VoidPtr
        self.TypeRefPtr = self.VoidPtrPtr
        self.ContextRef = self.VoidPtr
        self.ValueRef = self.VoidPtr
        self.ValueRefPtr = self.VoidPtrPtr
        self.GenericValueRef = self.VoidPtr
        self.BasicBlockRef = self.VoidPtr
        self.BuilderRef = self.VoidPtr
        self.TargetDataRef = self.VoidPtr
        self.Bool = lltype.Signed #LLVMBOOL is typedefed to int32
        self.Str = rffi.CONST_CCHARP
        self.VerifierFailureAction = self.Enum
        self.RealPredicate = self.Enum
        self.IntPredicate = self.Enum
        self.TargetDataRef = self.VoidPtr
