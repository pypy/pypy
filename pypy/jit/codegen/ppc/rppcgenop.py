from pypy.jit.codegen.model import AbstractRGenOp, CodeGenBlock, CodeGenerator
from pypy.jit.codegen.model import GenVar, GenConst
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.objectmodel import specialize

class GPRVar(GenVar):

    def __init__(self, number):
        self.number = number

    def load(self, builder):
        return self.number

    def __repr__(self):
        return 'r%d' % (self.number,)

class FPRVar(GenVar):

    def __init__(self, number):
        self.number = number

    def load(self, builder):
        return self.number

    def __repr__(self):
        return 'fr%d' % (self.number,)

class StackVar(GenVar):

    def __init__(self, location):
        self.location = location

    def load(self, builder):
        XXX

    def __repr__(self):
        return 'stackvar %d' % (self.location,)

class IntConst(GenConst):

    def __init__(self, value):
        self.value = value

    def load(self, builder):
        r = builder.newvar()
        builder.asm.load_word(r.number, self.value)
        return r.number

    @specialize.arg(1)
    def revealconst(self, T):
        if isinstance(T, lltype.Ptr):
            return lltype.cast_int_to_ptr(T, self.value)
        elif T is llmemory.Address:
            return llmemory.cast_int_to_adr(self.value)
        else:
            return lltype.cast_primitive(T, self.value)

    def __repr__(self):
        return "const=%r" % (self.value,)


from pypy.jit.codegen.ppc import codebuf_posix as memhandler
from ctypes import POINTER, cast, c_char, c_void_p, CFUNCTYPE, c_int

PTR = memhandler.PTR

class CodeBlockOverflow(Exception):
    pass

from pypy.translator.asm.ppcgen.rassemblermaker import make_rassembler
from pypy.translator.asm.ppcgen.ppc_assembler import MyPPCAssembler

RPPCAssembler = make_rassembler(MyPPCAssembler)

def emit(self, value):
    self.mc.write(value)
RPPCAssembler.emit = emit

class MachineCodeBlock:

    def __init__(self, map_size):
        assert map_size % 4 == 0
        res = memhandler.alloc(map_size)
        self._data = cast(res, POINTER(c_int * (map_size / 4)))
        self._size = map_size/4
        self._pos = 0

    def write(self, data):
         p = self._pos
         if p >= self._size:
             raise CodeBlockOverflow
         self._data.contents[p] = data
         self._pos = p + 1

    def tell(self):
        baseaddr = cast(self._data, c_void_p).value
        return baseaddr + self._pos * 4

    def __del__(self):
        memhandler.free(cast(self._data, PTR), self._size)

    def execute(self, arg1, arg2):
        fnptr = cast(self._data, binaryfn)
        return fnptr(arg1, arg2)

binaryfn = CFUNCTYPE(c_int, c_int, c_int)    # for testing

class Builder(CodeGenerator):

    def __init__(self, rgenop, mc, stackdepth):
        self.rgenop = rgenop
        self.stackdepth = stackdepth
        self.asm = RPPCAssembler()
        self.asm.mc = mc
        self.curreg = 3

    def _write_prologue(self, sigtoken):
        numargs = sigtoken     # for now
        self.curreg += numargs
        #self.asm.tw(31, 0, 0) # "trap"
        return [GPRVar(pos) for pos in range(3, 3+numargs)]

    def _close(self):
        self.rgenop.close_mc(self.asm.mc)
        self.asm.mc = None

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        genmethod = getattr(self, 'op_' + opname)
        return genmethod(gv_arg1, gv_arg2)

    def finish_and_return(self, sigtoken, gv_returnvar):
        self.asm.mr(3, gv_returnvar.load(self))
        self.asm.blr()
        self._close()

    def newvar(self):
        d = self.curreg
        self.curreg += 1
        assert d < 12
        return GPRVar(d)

    def op_int_add(self, gv_x, gv_y):
        gv_result = self.newvar()
        self.asm.add(gv_result.load(self),
                     gv_x.load(self),
                     gv_y.load(self))
        return gv_result

class RPPCGenOp(AbstractRGenOp):
    from pypy.jit.codegen.i386.codebuf import MachineCodeBlock

    def __init__(self):
        self.mcs = []   # machine code blocks where no-one is currently writing


    def __init__(self):
        self.mcs = []   # machine code blocks where no-one is currently writing

    def open_mc(self):
        if self.mcs:
            # XXX think about inserting NOPS for alignment
            return self.mcs.pop()
        else:
            return MachineCodeBlock(65536)   # XXX supposed infinite for now

    def close_mc(self, mc):
        self.mcs.append(mc)

    @staticmethod
    @specialize.memo()
    def sigToken(FUNCTYPE):
        return len(FUNCTYPE.ARGS)     # for now

    def openbuilder(self, stackdepth):
        return Builder(self, self.open_mc(), stackdepth)

    def newgraph(self, sigtoken):
        numargs = sigtoken          # for now
        initialstackdepth = numargs+1
        builder = self.openbuilder(initialstackdepth)
        entrypoint = builder.asm.mc.tell()
        inputargs_gv = builder._write_prologue(sigtoken)
        return builder, entrypoint, inputargs_gv


    @staticmethod
    @specialize.genconst(0)
    def genconst(llvalue):
        T = lltype.typeOf(llvalue)
        if isinstance(T, lltype.Primitive):
            return IntConst(lltype.cast_primitive(lltype.Signed, llvalue))
        elif T is llmemory.Address:
            return AddrConst(llvalue)
        elif isinstance(T, lltype.Ptr):
            return AddrConst(llmemory.cast_ptr_to_adr(llvalue))
        else:
            assert 0, "XXX not implemented"

    def gencallableconst(self, sigtoken, name, entrypointaddr):
        return IntConst(entrypointaddr)
