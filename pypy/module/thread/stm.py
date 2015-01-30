"""
Redirect some classes from pypy.module.pypystm.
"""

from pypy.module.pypystm import threadlocals, local

STMThreadLocals = threadlocals.STMThreadLocals
STMLocal = local.STMLocal
