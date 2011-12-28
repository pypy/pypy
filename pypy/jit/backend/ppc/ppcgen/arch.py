# Constants that depend on whether we are on 32-bit or 64-bit

from pypy.jit.backend.ppc.ppcgen.register import (NONVOLATILES,
                                                  NONVOLATILES_FLOAT,
                                                  MANAGED_REGS)

import sys
if sys.maxint == (2**31 - 1):
    WORD = 4
    IS_PPC_32 = True
    BACKCHAIN_SIZE = 2
else:
    WORD = 8
    IS_PPC_32 = False
    BACKCHAIN_SIZE = 6

DWORD                   = 2 * WORD
IS_PPC_64               = not IS_PPC_32
MY_COPY_OF_REGS         = 0

FORCE_INDEX             = WORD
GPR_SAVE_AREA           = len(NONVOLATILES) * WORD
FPR_SAVE_AREA           = len(NONVOLATILES_FLOAT) * DWORD
FLOAT_INT_CONVERSION    = WORD
MAX_REG_PARAMS          = 8

FORCE_INDEX_OFS         = len(MANAGED_REGS) * WORD
