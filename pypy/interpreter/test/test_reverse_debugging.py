import dis
from pypy.interpreter.reverse_debugging import *


class FakeCode:
    def __init__(self, co_code, co_lnotab):
        self.co_firstlineno = 43
        self.co_code = co_code
        self.co_lnotab = co_lnotab
        self.co_revdb_linestarts = None


def test_build_co_revdb_linestarts():
    fake_lnotab = ("\x01\x02\x03\x04"
                   "\x00\xFF\x20\x30\x00\xFF\x00\x40"
                   "\xFF\x00\x0A\x0B\xFF\x00\x0C\x00")
    code = FakeCode("?" * sum(map(ord, fake_lnotab[0::2])), fake_lnotab)
    lstart = build_co_revdb_linestarts(code)
    assert lstart is code.co_revdb_linestarts

    expected_starts = set()
    for addr, lineno in dis.findlinestarts(code):
        expected_starts.add(addr)

    for index in range(len(code.co_code)):
        c = lstart[index >> 3]
        found = ord(c) & (1 << (index & 7))
        assert (found != 0) == (index in expected_starts)
