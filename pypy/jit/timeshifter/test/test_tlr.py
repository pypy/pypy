from pypy.rpython.lltypesystem.rstr import string_repr
from pypy.jit.timeshifter.test.test_timeshift import timeshift
from pypy.jit.timeshifter.test.test_vlist import P_OOPSPEC

from pypy.jit.tl import tlr


def test_tlr():
    bytecode = string_repr.convert_const(tlr.SQUARE)
    insns, res = timeshift(tlr.interpret, [bytecode, 9], [0], policy=P_OOPSPEC)
    assert res == 81
