from rpython.rlib.rarithmetic import LONG_BIT, intmask, r_uint
from rpython.rlib.rbigint import rbigint, ONERBIGINT

from rpython.jit.metainterp.history import ConstInt
from rpython.jit.metainterp.resoperation import ResOperation, rop


# Logic to replace the signed integer division by a constant
# by a few operations involving a UINT_MUL_HIGH.


def magic_numbers(m):
    assert m == intmask(m)
    assert m & (m-1) != 0    # not a power of two
    assert m >= 3
    i = 1
    while (r_uint(1) << (i+1)) < r_uint(m):
        i += 1

    # k = 2**(64+i) // m + 1, computed manually using rbigint
    #                         because that's the easiest
    k1 = ONERBIGINT.lshift(LONG_BIT + i).floordiv(rbigint.fromint(m))
    k = k1.touint() + r_uint(1)

    assert k != r_uint(0)
    # Proof that k < 2**64 holds in all cases, even with the "+1":
    #
    # starting point: 2**i < m < 2**(i+1)  with i <= 63
    # 2**i < m
    # 2**i <= m - (2.0**(i-63))  as real number, because (2.0**(i-63))<=1.0
    # 2**(64+i) <= 2**64 * m - 2**(i+1)   as integers again
    # 2**(64+i) < 2**64 * m - m
    # 2**(64+i) / float(m) < 2**64-1    real numbers division
    # 2**(64+i) // m < 2**64-1    with the integer division
    #       k        < 2**64

    assert k > (r_uint(1) << (LONG_BIT-1))

    return (k, i)


def division_operations(n_box, m, known_nonneg=False):
    kk, ii = magic_numbers(m)

    # Turn the division into:
    #     t = n >> 63            # t == 0 or t == -1
    #     return (((n^t) * k) >> (64 + i)) ^ t

    # Proof that this gives exactly a = n // m = floor(q), where q
    # is the real number quotient:
    #
    # case t == 0, i.e. 0 <= n < 2**63
    #
    #     a <= q <= a + (m-1)/m     (we use '/' for the real quotient here)
    #    
    #     n * k == n * (2**(64+i) // m + 1)
    #           == n * ceil(2**(64+i) / m)
    #           == n * (2**(64+i) / m + ferr)         for 0 < ferr < 1
    #           == q * 2**(64+i) + err                for 0 < err < n
    #           <  q * 2**(64+i) + n
    #           <= (a + (m-1)/m) * 2**(64+i) + n
    #           == 2**(64+i) * (a + extra)            for 0 <= extra < ?
    #    
    #     extra == (m-1)/m + (n / 2**(64+i))
    #    
    #     but  n < 2**63 < 2**(64+i)/m  because  m < 2**(i+1)
    #    
    #     extra < (m-1)/m + 1/m
    #     extra < 1.
    #
    # case t == -1, i.e. -2**63 <= n <= -1
    #
    #     (note that n^(-1) == ~n)
    #     0 <= ~n < 2**63
    #     by the previous case we get an answer a == (~n) // m
    #     ~a == n // m    because it's a division truncating towards -inf.

    if not known_nonneg:
        t_box = ResOperation(rop.INT_RSHIFT, [n_box, ConstInt(LONG_BIT - 1)])
        nt_box = ResOperation(rop.INT_XOR, [n_box, t_box])
    else:
        t_box = None
        nt_box = n_box
    mul_box = ResOperation(rop.UINT_MUL_HIGH, [nt_box, ConstInt(intmask(kk))])
    sh_box = ResOperation(rop.UINT_RSHIFT, [mul_box, ConstInt(ii)])
    if not known_nonneg:
        final_box = ResOperation(rop.INT_XOR, [sh_box, t_box])
        return [t_box, nt_box, mul_box, sh_box, final_box]
    else:
        return [mul_box, sh_box]


def unsigned_mul_high(a, b):
    DIGIT = LONG_BIT / 2
    MASK = (1 << DIGIT) - 1

    ah = a >> DIGIT
    al = a & MASK
    bh = b >> DIGIT
    bl = b & MASK

    rll = al * bl; assert rll == r_uint(rll)
    rlh = al * bh; assert rlh == r_uint(rlh)
    rhl = ah * bl; assert rhl == r_uint(rhl)
    rhh = ah * bh; assert rhh == r_uint(rhh)

    r1 = (rll >> DIGIT) + rhl
    assert r1 == r_uint(r1)

    r1 = r_uint(r1)
    r2 = r_uint(r1 + rlh)
    borrow = (r2 < r1) << DIGIT

    r3 = (r2 >> DIGIT) + borrow + rhh
    assert r3 == r_uint(r3)
    return r3
