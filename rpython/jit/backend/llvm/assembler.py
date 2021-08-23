from rpython.jit.backend.model import CompiledLoopToken
from rpython.jit.backend.llsupport.assembler import BaseAssembler
from rpython.rtyper.lltypesystem import lltype
from rpython.jit.backend.llvm.llvm_api import CString
from rpython.jit.backend.llsupport import jitframe
from rpython.rtyper.lltypesystem.rffi import constcharp2str

class LLVMAssembler(BaseAssembler):
    def __init__(self, cpu, optimise=True):
        self.cpu = cpu
        self.llvm = cpu.llvm
        self.debug = cpu.debug
        self.optimise = optimise
        self.last_resource_tracker = None
        self.llvm.InitializeNativeTarget(None)
        self.llvm.InitializeNativeAsmPrinter(None)
        self.initialise_jit()
        self.pass_manager1 = self.llvm.CreatePassManager(None)
        self.pass_manager = self.llvm.CreatePassManager(None)
        self.add_opt_passes()

    def initialise_jit(self):
        jit_builder = self.llvm.CreateLLJITBuilder(None)
        if self.debug and jit_builder._cast_to_int() == 0:
            raise Exception("JIT Builder is Null")
        self.cpu_name = self.llvm.GetHostCPUName(None)
        self.cpu_features = self.llvm.GetHostCPUFeatures(None)
        self.triple = self.llvm.GetTargetTriple(None)
        target = self.llvm.GetTarget(self.triple)
        enums = lltype.malloc(self.llvm.JITEnums, flavor='raw')
        self.llvm.SetJITEnums(enums)
        opt_level = enums.codegenlevel
        reloc_mode = enums.reloc
        code_model = enums.codemodel
        self.target_machine = self.llvm.CreateTargetMachine(
            target, self.triple, self.cpu_name, self.cpu_features,
            opt_level, reloc_mode, code_model
        )
        lltype.free(enums, flavor='raw')
        self.data_layout = self.llvm.CreateTargetDataLayout(self.target_machine)
        jit_target_machine_builder = self.llvm.JITTargetMachineBuilderCreateFromTargetMachine(
                                            self.target_machine)
        self.llvm.LLJITBuilderSetJITTargetMachineBuilder(jit_builder,
                                                         jit_target_machine_builder)

        self.LLJIT = self.llvm.CreateLLJIT(jit_builder)
        if self.debug and self.LLJIT._cast_to_int() == 0:
            raise Exception("Failed To Create JIT")
        self.DyLib = self.llvm.LLJITGetMainJITDylib(self.LLJIT)
        if self.debug and self.DyLib._cast_to_int() == 0:
            raise Exception("DyLib is Null")

        self.llvm.AddDynamicLibrarySearchGenerator(self.LLJIT, self.DyLib)

    def jit_compile(self, module, looptoken, inputargs, dispatcher,
                    jitframe_depth, name, is_bridge=False):
        if self.last_resource_tracker is not None:
            failure = self.llvm.ResourceTrackerRemove(self.last_resource_tracker)
            if self.debug and failure._cast_to_int():
                print(constcharp2str(self.llvm.GetErrorMessage(failure)))
                raise Exception("Failed to remove old resource tracker")
        if is_bridge:
            clt = looptoken.compiled_loop_token
            clt.compiling_a_bridge()
        else:
            clt = CompiledLoopToken(self.cpu, looptoken.number)
            looptoken.compiled_loop_token = clt
        resource_tracker = self.llvm.CreateResourceTracker(self.DyLib)
        self.last_resource_tracker = resource_tracker
        clt._debug_nbargs = dispatcher.args_size/self.cpu.WORD
        locs = [self.cpu.WORD*i for i in range(len(inputargs))]
        clt._ll_initial_locs = locs
        frame_info = lltype.malloc(jitframe.JITFRAMEINFO, flavor='raw')
        frame_info.jfi_frame_depth = jitframe_depth
        frame_size = dispatcher.args_size + self.cpu.WORD
        + dispatcher.local_vars_size #args+ret addr+vars
        frame_info.jfi_frame_size = frame_size
        clt.frame_info = frame_info

        module_copy = self.llvm.CloneModule(module) #if we want to mutate module later to patch in a bridge we have to pass a copy to be owned by LLVM's JIT
        if not self.debug or self.optimise:
            self.llvm.RunPassManager(self.pass_manager1, module_copy)
            self.llvm.RunPassManager(self.pass_manager, module_copy)
        if self.debug:
            self.cpu.write_ir(module_copy, "opt")
        ctx = self.cpu.thread_safe_context
        thread_safe_module = self.llvm.CreateThreadSafeModule(module_copy, ctx)
        if self.debug and thread_safe_module._cast_to_int() == 0:
            raise Exception("TSM is Null")
        failure = self.llvm.LLJITAddModule(self.LLJIT,
                                           resource_tracker,
                                           thread_safe_module) #looking up a symbol in a module added to the LLVM Orc JIT invokes JIT compilation of the whole module
        if self.debug and failure._cast_to_int():
            print(constcharp2str(self.llvm.GetErrorMessage(failure)))
            raise Exception("Failed To Add Module To JIT")
        cstring = CString(name)
        addr = self.llvm.LLJITLookup(self.LLJIT,
                                     cstring.ptr)._cast_to_int()
        # import pdb
        # pdb.set_trace()
        # self.llvm.create_breakpoint()
        if self.debug and addr == 0:
            raise Exception("Trace Function is Null")
        looptoken._ll_function_addr = addr

    def add_opt_passes(self):
        self.llvm.AddTargetAnalysisPasses(self.pass_manager1, self.target_machine)
        self.llvm.AddTargetLibraryInfoPass(self.pass_manager, self.triple)
        self.llvm.AddBasicAliasAnalysisPass(self.pass_manager)
        self.llvm.AddScopedNoAliasAAPass(self.pass_manager)
        self.llvm.AddTypeBasedAliasAnalysisPass(self.pass_manager)
        self.llvm.AddInferFunctionAttrsPass(self.pass_manager)
        self.llvm.AddCFGSimplificationPass(self.pass_manager)
        self.llvm.AddScalarReplAggregatesPass(self.pass_manager)
        self.llvm.AddEarlyCSEPass(self.pass_manager)
        self.llvm.AddJumpThreadingPass(self.pass_manager)
        self.llvm.AddCorrelatedValuePropagationPass(self.pass_manager)
        self.llvm.AddReassociatePass(self.pass_manager)
        self.llvm.AddGVNPass(self.pass_manager)
        self.llvm.AddInstructionCombiningPass(self.pass_manager)
        self.llvm.AddInstructionSimplifyPass(self.pass_manager)
        self.llvm.AddMergedLoadStoreMotionPass(self.pass_manager)
        self.llvm.AddSCCPPass(self.pass_manager)
        self.llvm.AddDCEPass(self.pass_manager)
        self.llvm.AddAggressiveInstCombinerPass(self.pass_manager)
        self.llvm.AddIndVarSimplifyPass(self.pass_manager)
        self.llvm.AddLoopSimplifyPass(self.pass_manager)
        self.llvm.AddLoopRotatePass(self.pass_manager)
        self.llvm.AddLoopIdiomPass(self.pass_manager)
        self.llvm.AddLICMPass(self.pass_manager)
        self.llvm.AddLoopUnswitchPass(self.pass_manager)
        self.llvm.AddLICMPass(self.pass_manager)
        self.llvm.AddLoopUnswitchPass(self.pass_manager)
        self.llvm.AddLoopStrengthReducePass(self.pass_manager)
        self.llvm.AddCFGSimplificationPass(self.pass_manager)
        self.llvm.AddLoopVectorizePass(self.pass_manager)
        self.llvm.AddInstructionCombiningPass(self.pass_manager)
        self.llvm.AddSLPVectorizePass(self.pass_manager)

    def __del__(self):
        self.llvm.DisposePassManager(self.pass_manager)
