from rpython.jit.backend.llsupport.llmodel import AbstractLLCPU
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rtyper.lltypesystem.rffi import str2constcharp, constcharp2str
from rpython.rtyper.tool.rffi_platform import DefinedConstantInteger
from rpython.translator.tool.cbuild import ExternalCompilationInfo

class LLVM_CPU(AbstractLLCPU):
    def __init__(self, rtyper, stats, opts=None,
                 translate_support_code=False, gcdescr=None):
        AbstractLLCPU.__init__(self, rtyper, stats, opts,
                               translate_support_code, gcdescr)

        self.define_types()
        self.initialise_api()
        self.initialise_jit()

        self.Context = self.CreateThreadSafeContext(None)
        self.Module = self.CreateModule(str2constcharp("hot_code"))
        self.Builder = self.CreateBuilder(None)
        #data_layout = self.CreateTargetData(str2constcharp(
        #    "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128")) #TODO: make platform independant
        #self.SetModuleDataLayout(self.Module, data_layout)

    def initialise_jit(self):
        if self.InitializeNativeTarget(None): #returns 0 on success
            raise Exception("Native Target Failed To Initialise")
        if self.InitializeNativeAsmPrinter(None):
            raise Exception("Native Asmebly Printer Failed To Initialise")

        cpu_name = self.GetHostCPUName(None) #kept as C-string types
        cpu_features = self.GetHostCPUFeatures(None)
        triple = self.GetTargetTriple(None)
        target = self.GetTarget(triple)
        #if target._obj._getitem(0) == 0: #pointer is NULL
        #    raise Exception("Get Target From Triple Failed")
        opt_level = DefinedConstantInteger("LLVMCodeGenLevelNone") #TODO: are these the same as those offered by the pass manager?
        reloc_mode = DefinedConstantInteger("LLVMRelocDefault")
        code_model = DefinedConstantInteger("LLVMCodeModelJITDefault")

        data_layout = self.CreateTargetDataLayout(target)
        self.SetModuleDataLayout(self.Module, data_layout)

        target_machine = self.CreateTargetMachine(target, triple, cpu_name,
                                                  cpu_features, opt_level,
                                                  reloc_mode, code_model)
        jit_target_machine_builder = self.JITTargetMachineBuilderCreateFromTargetMachine(
                                            target_machine)
        jit_builder = self.CreateLLJITBuilder(None)
        self.LLJITBuilderSetJITTargetMachineBuilder(jit_builder,
                                                    jit_target_machine_builder)

        self.LLJIT = self.CreateLLJIT(jit_builder)
        self.DyLib = self.LLJITGetMainJITDylib(self.LLJIT)


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

        verified = self.VerifyModule(self.Module,
                                     DefinedConstantInteger("LLVMAbortProcessAction")) #for debugging
        if verified != 1:
            raise Exception("Malformed IR")

        looptoken.compiled_loop_token = self.compile_to_obj()
        lltype.free(arg_types, flavor='raw')

    def compile_to_obj(self):
        self.ThreadSafeModule = self.CreateThreadSafeModule(self.Module, self.Context)
        success = self.LLJITAddModule(self.LLJIT, self.DyLib, self.ThreadSafeModule) #looking up a symbol in a module added to the LLVM Orc JIT invokes JIT compilation of the whole module
        addr = self.LLJITLookup(self.LLJIT, "trace")
        return addr

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
        self.GetParam = rffi.llexternal("LLVMGetParam",
                                        [self.ValueRef, lltype.Signed],
                                        self.ValueRef, compilation_info=info)
        self.VerifyModule = rffi.llexternal("VerifyModule",
                                        [self.ModuleRef,
                                         self.VerifierFailureAction],
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
                                                      compilation_info=info) #following three functions are from our own libwrapper.so for functions defined statically which rffi can't see
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
        self.JITTargetMachineBuilderCreateFromTargetMachine = rffi.llexternal("LLVMOrcJITTargetMachineBuilderCreateFromTargetMachine",
                                                         [self.TargetMachineRef,
                                                          self.JITTargetMachineBuilderRef],
                                                        self.Void,
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
                                                          self.Enum],
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
