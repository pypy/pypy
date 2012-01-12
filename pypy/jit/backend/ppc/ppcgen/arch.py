# Constants that depend on whether we are on 32-bit or 64-bit

from pypy.jit.backend.ppc.ppcgen.register import (NONVOLATILES,
                                                  NONVOLATILES_FLOAT,
                                                  MANAGED_REGS)

import sys
if sys.maxint == (2**31 - 1):
    WORD = 4
    DWORD = 2 * WORD
    IS_PPC_32 = True
    BACKCHAIN_SIZE = 2
    FPR_SAVE_AREA = len(NONVOLATILES_FLOAT) * DWORD
else:
    WORD = 8
    DWORD = 2 * WORD
    IS_PPC_32 = False
    BACKCHAIN_SIZE = 6
    FPR_SAVE_AREA = len(NONVOLATILES_FLOAT) * WORD

IS_PPC_64               = not IS_PPC_32
MY_COPY_OF_REGS         = 0

FORCE_INDEX             = WORD
GPR_SAVE_AREA           = len(NONVOLATILES) * WORD
FLOAT_INT_CONVERSION    = WORD
MAX_REG_PARAMS          = 8
# we need at most 5 instructions to load a constant
# and one instruction to patch the stack pointer
SIZE_LOAD_IMM_PATCH_SP  = 6

FORCE_INDEX_OFS         = len(MANAGED_REGS) * WORD
