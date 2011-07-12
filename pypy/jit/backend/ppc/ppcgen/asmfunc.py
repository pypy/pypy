import py
import mmap, struct
from pypy.jit.backend.ppc.codebuf import MachineCodeBlockWrapper
from pypy.jit.backend.llsupport.asmmemmgr import AsmMemoryManager
from pypy.rpython.lltypesystem import lltype, rffi

_ppcgen = None

def get_ppcgen():
    global _ppcgen
    if _ppcgen is None:
        _ppcgen = py.magic.autopath().dirpath().join('_ppcgen.c')._getpymodule()
    return _ppcgen

class AsmCode(object):
    def __init__(self, size):
        self.code = MachineCodeBlockWrapper()

    def emit(self, insn):
        bytes = struct.pack("i", insn)
        for byte in bytes:
            self.code.writechar(byte)

    def get_function(self):
        i = self.code.materialize(AsmMemoryManager(), [])
        t = lltype.FuncType([], lltype.Signed)
        return rffi.cast(lltype.Ptr(t), i)
