from rpython.jit.metainterp.optimizeopt.intbounds import next_power2


def test_next_power2():
    assert next_power2(0) == 1
    assert next_power2(1) == 2
    assert next_power2(7) == 8
    assert next_power2(256) == 512
    assert next_power2(255) == 256
    assert next_power2(80) == 128
