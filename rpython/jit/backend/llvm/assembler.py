from rpython.jit.backend.model import CompiledLoopToken
from rpython.jit.backend.llsupport.assembler import BaseAssembler
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rtyper.lltypesystem.rffi import str2constcharp, constcharp2str

class LLVM_Assembler(BaseAssembler):
    def __init__(self, cpu, debug=False):
        self.cpu = cpu
        self.llvm = cpu.llvm
        self.debug = debug

    def JIT_compile(self, module, looptoken, inputargs):
        clt = CompiledLoopToken(self.cpu, looptoken.number)

        #CompiledLoopToken doesn't have this, and several other, attritubtes that I see the x86 backend define, not sure how it's doing that
        #if self.debug:
        #    clt._debug_nbargs = len(inputargs)

        looptoken.compiled_loop_token = clt
        ThreadSafeModule = self.llvm.CreateThreadSafeModule(module,
                                                                 self.cpu.ThreadSafeContext)
        if self.debug and ThreadSafeModule._cast_to_int() == 0:
            raise Exception("TSM is Null")

        failure = self.llvm.LLJITAddModule(self.llvm.LLJIT, self.llvm.DyLib,
                                           ThreadSafeModule) #looking up a symbol in a module added to the LLVM Orc JIT invokes JIT compilation of the whole module
        if self.debug and failure._cast_to_int():
            raise Exception("Failed To Add Module To JIT")

        addr = self.llvm.LLJITLookup(self.llvm.LLJIT, str2constcharp("trace"))._cast_to_int()
        if self.debug and addr == 0:
            raise Exception("trace Function is Null")

        looptoken._ll_function_addr = addr
