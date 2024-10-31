import sys

def test_sys_exception():
    assert sys.exception() is None
    try:
        1/0
    except ZeroDivisionError as e:
        assert sys.exception() is e
