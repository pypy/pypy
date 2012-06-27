
import pypy.rlib.rcomplex as c


def test_add():
    for c1, c2, result in [
        ((0, 0), (0, 0), (0, 0)),
        ((1, 0), (2, 0), (3, 0)),
        ((0, 3), (0, 2), (0, 5)),
        ((10., -3.), (-5, 7), (5, 4)),
    ]:
        assert c.c_add(c1, c2) == result

def test_sub():
    for c1, c2, result in [
            ((0, 0), (0, 0), (0, 0)),
            ((1, 0), (2, 0), (-1, 0)),
            ((0, 3), (0, 2), (0, 1)),
            ((10, -3), (-5, 7), (15, -10)),
            ((42, 0.3), (42, 0.3), (0, 0))
        ]:
            assert c.c_sub(c1, c2) == result 

def test_mul():
   for c1, c2, result in [
            ((0, 0), (0, 0), (0, 0)),
            ((1, 0), (2, 0), (2, 0)),
            ((0, 3), (0, 2), (-6, 0)),
            ((0, -3), (-5, 0), (0, 15)),
        ]:
            assert c.c_mul(c1, c2) == result