from rpython.jit.backend.model import CompiledLoopToken
from rpython.jit.backend.llsupport.assembler import BaseAssembler
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rtyper.lltypesystem.rffi import str2constcharp, constcharp2str
from rpython.jit.backend.llsupport.asmmemmgr import MachineDataBlockWrapper
from rpython.jit.backend.llsupport import jitframe

class LLVMAssembler(BaseAssembler):
    def __init__(self, cpu, debug=False):
        self.cpu = cpu
        self.llvm = cpu.llvm
        self.debug = debug

    def jit_compile(self, module, looptoken, inputargs, dispatcher):
        clt = CompiledLoopToken(self.cpu, looptoken.number)
        looptoken.compiled_loop_token = clt
        clt._debug_nbargs = dispatcher.args_size/self.cpu.WORD
        locs = [self.cpu.WORD*i for i in range(len(inputargs))]
        clt._ll_initial_locs = locs
        frame_info = lltype.malloc(jitframe.JITFRAMEINFO, flavor='raw')
        frame_info.jfi_frame_depth = 8 #this field doesn't map into an LLVM backend well, hoping this will do
        frame_size = dispatcher.args_size + self.cpu.WORD
        + dispatcher.local_vars_size #args+ret addr+vars
        frame_info.jfi_frame_size = frame_size
        clt.frame_info = frame_info

        module_copy = self.llvm.CloneModule(module) #if we want to mutate module later to patch in a bridge we have to pass a copy to be owned by LLVM's JIT
        #TODO: look into possible memory leak, though the JIT takes ownership not sure when it actually free's the module
        thread_safe_module = self.llvm.CreateThreadSafeModule(module_copy,
                                                              self.cpu.thread_safe_context)
        if self.debug and thread_safe_module._cast_to_int() == 0:
            raise Exception("TSM is Null")

        failure = self.llvm.LLJITAddModule(self.llvm.LLJIT,
                                           self.llvm.DyLib,
                                           thread_safe_module) #looking up a symbol in a module added to the LLVM Orc JIT invokes JIT compilation of the whole module
        if self.debug and failure._cast_to_int():
            raise Exception("Failed To Add Module To JIT")

        addr = self.llvm.LLJITLookup(self.llvm.LLJIT,
                                     str2constcharp("trace"))._cast_to_int()
        if self.debug and addr == 0:
            raise Exception("trace Function is Null")

        looptoken._ll_function_addr = addr
