import py
import mmap, struct

from pypy.jit.backend.ppc.codebuf import MachineCodeBlockWrapper
from pypy.jit.backend.llsupport.asmmemmgr import AsmMemoryManager
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.jit.backend.ppc.arch import IS_PPC_32, IS_PPC_64, WORD

_ppcgen = None

def get_ppcgen():
    global _ppcgen
    if _ppcgen is None:
        _ppcgen = py.magic.autopath().dirpath().join('_ppcgen.c')._getpymodule()
    return _ppcgen

class AsmCode(object):
    def __init__(self, size):
        self.code = MachineCodeBlockWrapper()
        if IS_PPC_64:
            # allocate function descriptor - 3 doublewords
            self.emit(0)
            self.emit(0)
            self.emit(0)
            self.emit(0)
            self.emit(0)
            self.emit(0)

    def emit(self, insn):
        bytes = struct.pack("i", insn)
        for byte in bytes:
            self.code.writechar(byte)

    def get_function(self):
        i = self.code.materialize(AsmMemoryManager(), [])
        if IS_PPC_64:
            p = rffi.cast(rffi.CArrayPtr(lltype.Signed), i)
            p[0] = i + 3*WORD
            # p[1], p[2] = ??
        t = lltype.FuncType([], lltype.Signed)
        return rffi.cast(lltype.Ptr(t), i)
