# Constants that depend on whether we are on 32-bit or 64-bit

from pypy.jit.backend.ppc.ppcgen.register import NONVOLATILES

import sys
if sys.maxint == (2**31 - 1):
    WORD = 4
    IS_PPC_32 = True
    IS_PPC_64 = False
else:
    WORD = 8
    IS_PPC_32 = False
    IS_PPC_64 = True

MY_COPY_OF_REGS = 0

GPR_SAVE_AREA   = len(NONVOLATILES) * WORD
MAX_REG_PARAMS = 8
