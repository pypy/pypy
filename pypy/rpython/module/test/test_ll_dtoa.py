from pypy.rpython.module.ll_dtoa import strtod, dtoa, rarithmetic

def test_strtod():
    assert strtod("12345") == 12345.0
    assert strtod("1.1") == 1.1
    assert strtod("3.47") == 3.47
    raises(ValueError, strtod, "123A")

def test_dtoa():
    assert dtoa(3.47) == "3.47"
    assert dtoa(1.1) == "1.1"
    assert dtoa(-1.1) == "-1.1"
    assert dtoa(1.1, flags=rarithmetic.DTSF_SIGN) == "+1.1"
    assert dtoa(12.3577) == "12.3577"
    assert dtoa(10.0) == "10"
    assert dtoa(1.0e100) == "1" + "0" * 100
