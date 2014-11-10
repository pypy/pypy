"""
Redirect some classes from pypy.module._stm.
"""

from pypy.module._stm import threadlocals, local

STMThreadLocals = threadlocals.STMThreadLocals
STMLocal = local.STMLocal
