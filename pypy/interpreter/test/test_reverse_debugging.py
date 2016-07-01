import dis
from pypy.interpreter.reverse_debugging import *
from hypothesis import given, strategies, example


class FakeCode:
    hidden_applevel = False
    def __init__(self, co_code, co_lnotab):
        self.co_firstlineno = 43
        self.co_code = co_code
        self.co_lnotab = co_lnotab
        self.co_revdb_linestarts = None


@given(strategies.binary())
@example("\x01\x02\x03\x04"
         "\x00\xFF\x20\x30\x00\xFF\x00\x40"
         "\xFF\x00\x0A\x0B\xFF\x00\x0C\x00")
def test_build_co_revdb_linestarts(lnotab):
    if len(lnotab) & 1:
        lnotab = lnotab + '\x00'   # make the length even
    code = FakeCode("?" * sum(map(ord, lnotab[0::2])), lnotab)
    lstart = build_co_revdb_linestarts(code)
    assert lstart is code.co_revdb_linestarts

    expected_starts = set()
    for addr, lineno in dis.findlinestarts(code):
        expected_starts.add(addr)

    next_start = len(code.co_code)
    for index in range(len(code.co_code), -1, -1):
        if index in expected_starts:
            next_start = index
        assert lstart[index] == chr(next_start - index
                                    if next_start - index <= 255
                                    else 255)
