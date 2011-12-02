# Constants that depend on whether we are on 32-bit or 64-bit

from pypy.jit.backend.ppc.ppcgen.register import (NONVOLATILES,
                                                  NONVOLATILES_FLOAT)

import sys
if sys.maxint == (2**31 - 1):
    WORD = 4
    IS_PPC_32 = True
else:
    WORD = 8
    IS_PPC_32 = False

DWORD                   = 2 * WORD
BACKCHAIN_SIZE          = 6 * WORD
IS_PPC_64               = not IS_PPC_32
MY_COPY_OF_REGS         = 0

FORCE_INDEX             = WORD
GPR_SAVE_AREA           = len(NONVOLATILES) * WORD
FPR_SAVE_AREA           = len(NONVOLATILES_FLOAT) * DWORD
FLOAT_INT_CONVERSION    = 4 * WORD
MAX_REG_PARAMS          = 8
