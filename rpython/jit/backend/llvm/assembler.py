from rpython.jit.backend.model import CompiledLoopToken
from rpython.jit.backend.llsupport.assembler import BaseAssembler
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rtyper.lltypesystem.rffi import str2constcharp, constcharp2str

class LLVMAssembler(BaseAssembler):
    def __init__(self, cpu, debug=False):
        self.cpu = cpu
        self.llvm = cpu.llvm
        self.debug = debug

    def jit_compile(self, module, looptoken, inputargs):
        clt = CompiledLoopToken(self.cpu, looptoken.number)
        if self.debug:
            clt._debug_nbargs = len(inputargs)
        looptoken.compiled_loop_token = clt

        module_copy = self.llvm.CloneModule(module) #if we want to mutate module later to patch in a bridge we have to pass a copy to be owned by LLVM's JIT
        #TODO: look into possible memory leak, though the JIT takes ownership not sure when it actually free's the module
        thread_safe_module = self.llvm.CreateThreadSafeModule(module_copy,
                                                              self.cpu.context)
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
