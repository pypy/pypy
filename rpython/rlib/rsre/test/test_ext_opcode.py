"""
Test for cases that cannot be produced using the Python 2.7 sre_compile
module, but can be produced by other means (e.g. Python 3.5)
"""

from rpython.rlib.rsre import rsre_core
from rpython.rlib.rsre.rsre_char import MAXREPEAT

# import OPCODE_XX as XX
for name, value in rsre_core.__dict__.items():
    if name.startswith('OPCODE_') and isinstance(value, int):
        globals()[name[7:]] = value


def test_repeat_one_with_backref():
    # Python 3.5 compiles "(.)\1*" using REPEAT_ONE instead of REPEAT:
    # it's a valid optimization because \1 is always one character long
    r = [MARK, 0, ANY, MARK, 1, REPEAT_ONE, 6, 0, MAXREPEAT, 
         GROUPREF, 0, SUCCESS, SUCCESS]
    assert rsre_core.match(r, "aaa").match_end == 3

def test_min_repeat_one_with_backref():
    # Python 3.5 compiles "(.)\1*?b" using MIN_REPEAT_ONE
    r = [MARK, 0, ANY, MARK, 1, MIN_REPEAT_ONE, 6, 0, MAXREPEAT,
         GROUPREF, 0, SUCCESS, LITERAL, 98, SUCCESS]
    assert rsre_core.match(r, "aaab").match_end == 4
