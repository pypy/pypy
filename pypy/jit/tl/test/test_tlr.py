from pypy.jit.tl import tlr


def test_square():
    assert tlr.interpret(tlr.SQUARE, 1) == 1
    assert tlr.interpret(tlr.SQUARE, 7) == 49
    assert tlr.interpret(tlr.SQUARE, 9) == 81
