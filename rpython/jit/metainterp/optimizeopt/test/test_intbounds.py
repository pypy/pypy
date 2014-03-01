from rpython.jit.metainterp.optimizeopt.intbounds import next_pow2_m1


def test_next_pow2_m1():
    assert next_pow2_m1(0) == 0
    assert next_pow2_m1(1) == 1
    assert next_pow2_m1(7) == 7
    assert next_pow2_m1(256) == 511
    assert next_pow2_m1(255) == 255
    assert next_pow2_m1(80) == 127
    assert next_pow2_m1((1 << 32) - 5) == (1 << 32) - 1
    assert next_pow2_m1((1 << 64) - 1) == (1 << 64) - 1
