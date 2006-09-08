from pypy.jit.tl import tlr
from pypy.jit.tl.test.test_tl import translate
from pypy.jit.conftest import Benchmark


def test_square():
    assert tlr.interpret(tlr.SQUARE, 1) == 1
    assert tlr.interpret(tlr.SQUARE, 7) == 49
    assert tlr.interpret(tlr.SQUARE, 9) == 81

def test_translate():
    def driver():
        bench = Benchmark()
        while 1:
            res = tlr.interpret(tlr.SQUARE, 1764)
            if bench.stop():
                break
        return res

    fn = translate(driver, [])
    res = fn()
    assert res == 1764 * 1764
