from pypy.jit.codegen.ppc.ppc_assembler import MyPPCAssembler
from pypy.jit.codegen.ppc.func_builder import make_func

from regname import *

def access_at():
    a = MyPPCAssembler()

    a.lwzx(r3, r3, r4)
    a.blr()

    return make_func(a, "i", "ii")

access_at = access_at()

def itoO():
    a = MyPPCAssembler()

    a.blr()

    return make_func(a, "O", "i")

itoO = itoO()
