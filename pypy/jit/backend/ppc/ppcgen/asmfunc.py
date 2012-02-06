import py
import mmap, struct

from pypy.jit.backend.ppc.codebuf import MachineCodeBlockWrapper
from pypy.jit.backend.llsupport.asmmemmgr import AsmMemoryManager
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.jit.backend.ppc.ppcgen.arch import IS_PPC_32, IS_PPC_64, WORD
from pypy.rlib.rarithmetic import r_uint

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
            for i in range(6):
                self.emit(r_uint(0))

    def emit(self, word):
        self.code.writechar(chr((word >> 24) & 0xFF))
        self.code.writechar(chr((word >> 16) & 0xFF))
        self.code.writechar(chr((word >> 8) & 0xFF))
        self.code.writechar(chr(word & 0xFF))

    def get_function(self):
        i = self.code.materialize(AsmMemoryManager(), [])
        if IS_PPC_64:
            p = rffi.cast(rffi.CArrayPtr(lltype.Signed), i)
            p[0] = i + 3*WORD
            # p[1], p[2] = ??
        t = lltype.FuncType([], lltype.Signed)
        return rffi.cast(lltype.Ptr(t), i)
