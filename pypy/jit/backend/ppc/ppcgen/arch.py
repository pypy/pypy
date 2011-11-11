# Constants that depend on whether we are on 32-bit or 64-bit

from pypy.jit.backend.ppc.ppcgen.register import NONVOLATILES

import sys
if sys.maxint == (2**31 - 1):
    WORD = 4
    IS_PPC_32 = True
    BACKCHAIN_SIZE = 2 * WORD
else:
    WORD = 8
    IS_PPC_32 = False
    BACKCHAIN_SIZE = 3 * WORD

IS_PPC_64 = not IS_PPC_32
MY_COPY_OF_REGS = 0

GPR_SAVE_AREA   = len(NONVOLATILES) * WORD
MAX_REG_PARAMS = 8
