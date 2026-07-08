
"""
opcode module - potentially shared between dis and other modules which
operate on bytecodes (e.g. peephole optimizers).

This used to be a hand-maintained copy of the opcode table, which drifted out
of sync with the bytecode the interpreter actually emits (e.g. JUMP_ABSOLUTE
ended up at the wrong number).  It now re-exports PyPy's canonical opcode table
(pypy.tool.stdlib_opcode, which loads lib-python/3/opcode.py) so the
disassembler (dis3.py) and the __pytrace__ tracer always match the running
interpreter.
"""

from pypy.tool.stdlib_opcode import (
    opmap, opname, HAVE_ARGUMENT,
    hasconst, hasname, hasjrel, hasjabs,
    haslocal, hascompare, hasfree, cmp_op)

__all__ = ["cmp_op", "hasconst", "hasname", "hasjrel", "hasjabs",
           "haslocal", "hascompare", "hasfree", "opname", "opmap",
           "HAVE_ARGUMENT", "EXTENDED_ARG", "hasnargs"]

EXTENDED_ARG = opmap['EXTENDED_ARG']
hasnargs = []  # unused, kept for backwards compatibility

try:
    from _opcode import stack_effect
    __all__.append('stack_effect')
except ImportError:
    pass
