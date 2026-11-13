# XXX Check for win64:
# The win64 port of PyPy/RPython requires sys.maxint == sys.maxsize,
# this differs from the CPython implementation
# see comment at the top of rpython.rlib.rarithmetic for details.
# The rest of rpython/ spells it sys.maxsize, which relies on this check.
import sys
if getattr(sys, "maxint", sys.maxsize) != sys.maxsize:
    raise Exception(
        "Translating on win64 requires either a modified CPython "
        "(so-called CPython64/64) or a working win64 build of PyPy2.")
