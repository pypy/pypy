from pypy.jit.metainterp.optimizeopt.intutils import IntBound, IntUpperBound, \
     IntLowerBound, IntUnbounded
from copy import copy
import sys

def bound(a,b):
    if a is None and b is None:
        return IntUnbounded()
    elif a is None:
        return IntUpperBound(b)
    elif b is None:
        return IntLowerBound(a)
    else:
        return IntBound(a,b)

def const(a):
    return bound(a,a)

def some_bounds():
    brd = [None] + range(-2, 3)
    for lower in brd:
        for upper in brd:
            if lower is not None and upper is not None and lower > upper:
                continue
            yield (lower, upper, bound(lower, upper))

nbr = range(-5, 6)

def test_known():
    for lower, upper, b in some_bounds():
        inside = []
        border = []
        for n in nbr:
            if (lower is None or n >= lower) and \
               (upper is None or n <= upper):
                if n == lower or n ==upper:
                    border.append(n)
                else:
                    inside.append(n)
                    
        for n in nbr:
            c = const(n)
            if n in inside:
                assert b.contains(n)
                assert not b.known_lt(c)
                assert not b.known_gt(c)
                assert not b.known_le(c)
                assert not b.known_ge(c)
            elif n in border:
                assert b.contains(n)
                if n == upper:
                    assert b.known_le(const(upper))
                else:
                    assert b.known_ge(const(lower))
            else:
                assert not b.contains(n)
                some = (border + inside)[0]
                if n < some:
                    assert b.known_gt(c)
                else:
                    assert b.known_lt(c)


def test_make():                            
    for _, _, b1 in some_bounds():
        for _, _, b2 in some_bounds():
            lt = IntUnbounded()
            lt.make_lt(b1)
            lt.make_lt(b2)
            for n in nbr:
                c = const(n)
                if b1.known_le(c) or b2.known_le(c):
                    assert lt.known_lt(c)
                else:
                    assert not lt.known_lt(c)
                assert not lt.known_gt(c)
                assert not lt.known_ge(c)

            gt = IntUnbounded()
            gt.make_gt(b1)
            gt.make_gt(b2)
            for n in nbr:
                c = const(n)
                if b1.known_ge(c) or b2.known_ge(c):
                    assert gt.known_gt(c)
                else:
                    assert not gt.known_gt(c)
            assert not gt.known_lt(c)
            assert not gt.known_le(c)

            le = IntUnbounded()
            le.make_le(b1)
            le.make_le(b2)
            for n in nbr:
                c = const(n)
                if b1.known_le(c) or b2.known_le(c):
                    assert le.known_le(c)
                else:
                    assert not le.known_le(c)
                assert not le.known_gt(c)
                assert not le.known_ge(c)

                
            ge = IntUnbounded()
            ge.make_ge(b1)
            ge.make_ge(b2)
            for n in nbr:
                c = const(n)
                if b1.known_ge(c) or b2.known_ge(c):
                    assert ge.known_ge(c)
                else:
                    assert not ge.known_ge(c)
                assert not ge.known_lt(c)
                assert not ge.known_le(c)

            gl = IntUnbounded()
            gl.make_ge(b1)
            gl.make_le(b2)
            for n in nbr:
                c = const(n)
                if b1.known_ge(c):
                    assert gl.known_ge(c)
                else:
                    assert not gl.known_ge(c)
                    assert not gl.known_gt(c)
                if  b2.known_le(c):
                    assert gl.known_le(c)
                else:
                    assert not gl.known_le(c)
                    assert not gl.known_lt(c)

def test_intersect():                            
    for _, _, b1 in some_bounds():
        for _, _, b2 in some_bounds():
            b = copy(b1)
            b.intersect(b2)
            for n in nbr:
                if b1.contains(n) and b2.contains(n):
                    assert b.contains(n)
                else:
                    assert not b.contains(n)
                    
def test_add():
    for _, _, b1 in some_bounds():
        for n1 in nbr:
            b2 = b1.add(n1)
            for n2 in nbr:
                c1 = const(n2)
                c2 = const(n2 + n1)
                
                if b1.known_le(c1):
                    assert b2.known_le(c2)
                else:
                    assert not b2.known_le(c2)

                if b1.known_ge(c1):
                    assert b2.known_ge(c2)
                else:
                    assert not b2.known_ge(c2)

                if b1.known_le(c1):
                    assert b2.known_le(c2)
                else:
                    assert not b2.known_lt(c2)

                if b1.known_lt(c1):
                    assert b2.known_lt(c2)
                else:
                    assert not b2.known_lt(c2)

                if b1.known_gt(c1):
                    assert b2.known_gt(c2)
                else:
                    assert not b2.known_gt(c2)

def test_add_bound():
    for _, _, b1 in some_bounds():
        for _, _, b2 in some_bounds():
            b3 = b1.add_bound(b2)
            for n1 in nbr:
                for n2 in nbr:
                    if b1.contains(n1) and b2.contains(n2):
                        assert b3.contains(n1 + n2)

    a=bound(2, 4).add_bound(bound(1, 2))
    assert not a.contains(2)
    assert not a.contains(7)

def test_mul_bound():
    for _, _, b1 in some_bounds():
        for _, _, b2 in some_bounds():
            b3 = b1.mul_bound(b2)
            for n1 in nbr:
                for n2 in nbr:
                    if b1.contains(n1) and b2.contains(n2):
                        assert b3.contains(n1 * n2)

    a=bound(2, 4).mul_bound(bound(1, 2))
    assert not a.contains(1)
    assert not a.contains(9)

    a=bound(-3, 2).mul_bound(bound(1, 2))
    assert not a.contains(-7)
    assert not a.contains(5)
    assert a.contains(-6)
    assert a.contains(4)

    a=bound(-3, 2).mul(-1)
    for i in range(-2,4):
        assert a.contains(i)
    assert not a.contains(4)
    assert not a.contains(-3)

def test_shift_bound():
    for _, _, b1 in some_bounds():
        for _, _, b2 in some_bounds():
            bleft = b1.lshift_bound(b2)
            bright = b1.rshift_bound(b2)
            for n1 in nbr:
                for n2 in range(10):
                    if b1.contains(n1) and b2.contains(n2):
                        assert bleft.contains(n1 << n2)
                        assert bright.contains(n1 >> n2)

def test_shift_overflow():
    b10 = IntBound(0, 10)
    b100 = IntBound(0, 100)
    bmax = IntBound(0, sys.maxint/2)
    assert not b10.lshift_bound(b100).has_upper
    assert not bmax.lshift_bound(b10).has_upper
    assert b10.lshift_bound(b10).has_upper
    
def test_div_bound():
    for _, _, b1 in some_bounds():
        for _, _, b2 in some_bounds():
            b3 = b1.div_bound(b2)
            for n1 in nbr:
                for n2 in nbr:
                    if b1.contains(n1) and b2.contains(n2):
                        if n2 != 0:
                            assert b3.contains(n1 / n2)

    a=bound(2, 4).div_bound(bound(1, 2))
    assert not a.contains(0)
    assert not a.contains(5)

    a=bound(-3, 2).div_bound(bound(1, 2))
    assert not a.contains(-4)
    assert not a.contains(3)
    assert a.contains(-3)
    assert a.contains(0)



def test_sub_bound():
    for _, _, b1 in some_bounds():
        for _, _, b2 in some_bounds():
            b3 = b1.sub_bound(b2)
            for n1 in nbr:
                for n2 in nbr:
                    if b1.contains(n1) and b2.contains(n2):
                        assert b3.contains(n1 - n2)

    a=bound(2, 4).sub_bound(bound(1, 2))
    assert not a.contains(-1)
    assert not a.contains(4)
