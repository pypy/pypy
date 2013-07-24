from rpython.jit.backend.arm import support

def test_mod():
    assert support.arm_int_mod(10, 2) == 0
    assert support.arm_int_mod(11, 2) == 1
    assert support.arm_int_mod(11, 3) == 2

def test_mod2():
    assert support.arm_int_mod(-10, 2) == 0
    assert support.arm_int_mod(-11, 2) == -1
    assert support.arm_int_mod(-11, 3) == -2

def test_mod3():
    assert support.arm_int_mod(10, -2) == 0
    assert support.arm_int_mod(11, -2) == 1
    assert support.arm_int_mod(11, -3) == 2


def test_div():
    assert support.arm_int_div(-7, 2) == -3
    assert support.arm_int_div(9, 2) == 4
    assert support.arm_int_div(10, 5) == 2

