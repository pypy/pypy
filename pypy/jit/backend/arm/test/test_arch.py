from pypy.jit.backend.arm import arch
from pypy.jit.backend.arm.test.support import skip_unless_arm
skip_unless_arm()

def test_mod():
    assert arch.arm_int_mod(10, 2) == 0
    assert arch.arm_int_mod(11, 2) == 1
    assert arch.arm_int_mod(11, 3) == 2

def test_mod2():
    assert arch.arm_int_mod(-10, 2) == 0
    assert arch.arm_int_mod(-11, 2) == -1
    assert arch.arm_int_mod(-11, 3) == -2

def test_mod3():
    assert arch.arm_int_mod(10, -2) == 0
    assert arch.arm_int_mod(11, -2) == 1
    assert arch.arm_int_mod(11, -3) == 2


def test_div():
    assert arch.arm_int_div(-7, 2) == -3
    assert arch.arm_int_div(9, 2) == 4
    assert arch.arm_int_div(10, 5) == 2

