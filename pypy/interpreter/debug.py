"""
PyPy-oriented interface to pdb.
"""

import pdb, sys

def fire(operationerr):
    if not operationerr.debug_tbs:
        return
    tb = operationerr.debug_tbs[-1]
    pdb.post_mortem(tb)
