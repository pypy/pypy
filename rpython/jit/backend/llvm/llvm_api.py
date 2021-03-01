from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.translator.tool.cbuild import ExternalCompilationInfo

class LLVM_API:
    def __init__(self, debug=False):
        self.debug = debug #disable in prod to prevent castings and comparisons of returned values
        self.define_types()
        self.initialise_api()
        self.initialise_jit()

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
        self.JITDylibRef = self.VoidPtr
        self.ThreadSafeModuleRef = self.VoidPtr
        self.ThreadSafeContextRef = self.VoidPtr
        self.LLJITBuilderRef = self.VoidPtr
        self.LLJITRef = self.VoidPtr
        self.LLJITRefPtr = self.VoidPtrPtr
        self.ErrorRef = self.VoidPtr
        self.ExecutionSessionRef = self.VoidPtr
        self.JITTargetAddress = self.VoidPtr
        self.PassManagerRef = self.VoidPtrPtr
        self.JITTargetMachineBuilderRef = self.VoidPtr
        self.TargetMachineRef = self.VoidPtr
        self.TargetRef = self.VoidPtr

    def initialise_api(self):
        header_files = ["Core","Target","Analysis","DataTypes",
                        "Error","ErrorHandling","ExternC",
                        "Initialization","Orc","TargetMachine","Types"]
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
        self.GetInsertBlock = rffi.llexternal("LLVMGetInsertBlock",
                                        [self.BuilderRef],
                                        self.BasicBlockRef, compilation_info=info)
        self.GetParam = rffi.llexternal("LLVMGetParam",
                                        [self.ValueRef, lltype.Signed],
                                        self.ValueRef, compilation_info=info)
        self.VerifyModule = rffi.llexternal("VerifyModule",
                                            [self.ModuleRef],
                                        self.Bool,
                                        compilation_info=info)
        self.DisposeMessage = rffi.llexternal("LLVMDisposeMessage",
                                              [self.Str], self.Void,
                                              compilation_info=info)
        self.DisposeBuilder = rffi.llexternal("LLVMDisposeBuilder",
                                              [self.BuilderRef], self.Void,
                                              compilation_info=info)
        self.DiposeModule = rffi.llexternal("LLVMDisposeModule",
                                            [self.ModuleRef], self.Void,
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
        self.AddIncoming = rffi.llexternal("AddIncoming",
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
                                                      compilation_info=info)
        self.InitializeNativeAsmPrinter = rffi.llexternal("InitializeNativeAsmPrinter",
                                                          [self.Void], self.Bool,
                                                          compilation_info=info)
        self.CreateThreadSafeModule = rffi.llexternal("LLVMOrcCreateNewThreadSafeModule",
                                                         [self.ModuleRef,
                                                          self.ThreadSafeContextRef],
                                                        self.ThreadSafeModuleRef,
                                                         compilation_info=info)
        self.CreateThreadSafeContext = rffi.llexternal("LLVMOrcCreateNewThreadSafeContext",
                                                         [self.Void],
                                                       self.ThreadSafeContextRef,
                                                         compilation_info=info)
        self.GetContext = rffi.llexternal("LLVMOrcThreadSafeContextGetContext",
                                                         [self.ThreadSafeContextRef],
                                                       self.ContextRef,
                                                         compilation_info=info)
        self.LLJITLookup = rffi.llexternal("LLJITLookup",
                                                         [self.LLJITRef,
                                                          self.Str], self.JITTargetAddress,
                                                         compilation_info=info)
        self.LLJITAddModule = rffi.llexternal("LLVMOrcLLJITAddLLVMIRModule",
                                                         [self.LLJITRef,
                                                          self.JITDylibRef,
                                                          self.ThreadSafeModuleRef],
                                                        self.ErrorRef,
                                                         compilation_info=info)
        self.LLJITGetMainJITDylib = rffi.llexternal("LLVMOrcLLJITGetMainJITDylib",
                                                         [self.LLJITRef],
                                                        self.JITDylibRef,
                                                         compilation_info=info)
        self.LLJITGetExecutionSession = rffi.llexternal("LLVMOrcExecutionSessionRef",
                                                         [self.LLJITRef],
                                                        self.ExecutionSessionRef,
                                                         compilation_info=info)
        self.CreateLLJIT = rffi.llexternal("CreateLLJIT",
                                                        [self.LLJITBuilderRef],
                                                        self.LLJITRef,
                                                        compilation_info=info)
        self.CreateLLJITBuilder = rffi.llexternal("LLVMOrcCreateLLJITBuilder",
                                                         [self.Void],
                                                        self.LLJITBuilderRef,
                                                         compilation_info=info)
        self.CreatePassManager = rffi.llexternal("LLVMCreatePassManager",
                                                         [self.Void],
                                                        self.PassManagerRef,
                                                         compilation_info=info)
        self.RunPassManager = rffi.llexternal("LLVMRunPassManager",
                                                         [self.PassManagerRef,
                                                          self.ModuleRef], self.Bool,
                                                         compilation_info=info)
        self.LLJITBuilderSetJITTargetMachineBuilder = rffi.llexternal("LLVMOrcLLJITBuilderSetJITTargetMachineBuilder",
                                                         [self.LLJITBuilderRef,
                                                          self.JITTargetMachineBuilderRef],
                                                        self.Void,
                                                         compilation_info=info)
        self.JITTargetMachineBuilderCreateFromTargetMachine = rffi.llexternal("JITTargetMachineBuilderCreateFromTargetMachine",
                                                         [self.TargetMachineRef],
                                                        self.JITTargetMachineBuilderRef,
                                                        compilation_info=info)
        self.GetHostCPUName = rffi.llexternal("LLVMGetHostCPUName",
                                                         [self.Void],
                                                        self.Str,
                                                        compilation_info=info)
        self.GetHostCPUFeatures = rffi.llexternal("LLVMGetHostCPUFeatures",
                                                         [self.Void],
                                                        self.Str,
                                                        compilation_info=info)
        self.GetHostCPUFeatures = rffi.llexternal("LLVMGetHostCPUFeatures",
                                                         [self.Void],
                                                        self.Str,
                                                        compilation_info=info)
        self.CreateTargetMachine = rffi.llexternal("LLVMCreateTargetMachine",
                                                         [self.TargetRef,
                                                          self.Str, self.Str,
                                                          self.Str, self.Enum,
                                                          self.Enum, self.Enum],
                                                        self.TargetMachineRef,
                                                        compilation_info=info)
        self.GetTarget = rffi.llexternal("GetTargetFromTriple",
                                                         [self.Str],
                                                        self.TargetRef,
                                                        compilation_info=info)
        self.CreateTargetDataLayout = rffi.llexternal("LLVMCreateTargetDataLayout",
                                                         [self.TargetMachineRef],
                                                        self.TargetDataRef,
                                                        compilation_info=info)
        self.GetTargetTriple = rffi.llexternal("LLVMGetDefaultTargetTriple",
                                                         [self.Void],
                                                         self.Str,
                                                        compilation_info=info)
        self.GetParam =  rffi.llexternal("LLVMGetParam",[self.ValueRef, lltype.Signed],
                                                        self.ValueRef,
                                                        compilation_info=info)

    def initialise_jit(self):
        if self.debug:
            if self.InitializeNativeTarget(None): #returns 0 on success
                raise Exception("Native Target Failed To Initialise")
            if self.InitializeNativeAsmPrinter(None):
                raise Exception("Native Asmebly Printer Failed To Initialise")
        else:
            self.InitializeNativeTarget(None)
            self.InitializeNativeAsmPrinter(None)

        """
        commented code needs LLVM 12 to run
        """

        #cpu_name = self.GetHostCPUName(None) #kept as C-string types
        #cpu_features = self.GetHostCPUFeatures(None)
        #triple = self.GetTargetTriple(None)
        #target = self.GetTarget(triple)
        #if target._obj._getitem(0) == 0: #pointer is NULL
        #    raise Exception("Get Target From Triple Failed")
        #opt_level = DefinedConstantInteger("LLVMCodeGenLevelAggressive")
        #reloc_mode = DefinedConstantInteger("LLVMRelocDefault")
        #code_model = DefinedConstantInteger("LLVMCodeModelJITDefault")
        #target_machine = self.CreateTargetMachine(target, triple, cpu_name,
        #                                          cpu_features, opt_level,
        #                                          reloc_mode, code_model)
        #jit_target_machine_builder = self.JITTargetMachineBuilderCreateFromTargetMachine(
        #                                    target_machine)


        jit_builder = self.CreateLLJITBuilder(None)
        if self.debug and jit_builder._cast_to_int() == 0:
            raise Exception("JIT Builder is Null")

        #self.LLJITBuilderSetJITTargetMachineBuilder(jit_builder,
        #                                            jit_target_machine_builder)

        #data_layout = self.CreateTargetDataLayout(target_machine)
        #self.SetModuleDataLayout(self.Module, data_layout)

        self.LLJIT = self.CreateLLJIT(jit_builder)
        if self.debug and self.LLJIT._cast_to_int() == 0:
            raise Exception("Failed To Create JIT")
        self.DyLib = self.LLJITGetMainJITDylib(self.LLJIT)
        if self.debug and self.DyLib._cast_to_int() == 0:
            raise Exception("DyLib is Null")
