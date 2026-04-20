"""
Bytecode inspection for exception table Phase 7 work.
Run with:
  ~/oss/pypy2.7-v7.3.20-linux64/bin/pypy pytest.py pypy/interpreter/test/apptest_exctable_dis.py -s -v > /tmp/dis_pypy.txt 2>&1 &
Compare against CPython:
  python3.11 pytest.py -D pypy/interpreter/test/apptest_exctable_dis.py -s -v > /tmp/dis_cpython.txt 2>&1 &
"""
import dis


def _try_except_as():
    try:
        x = 1
    except ValueError as e:
        pass


def _try_except_no_name():
    try:
        x = 1
    except ValueError:
        pass


def _try_except_multi_handler():
    try:
        x = 1
    except TypeError as e:
        pass
    except ValueError as e:
        pass


def _try_finally():
    try:
        x = 1
    finally:
        pass


def _nested_try_except_in_except():
    try:
        x = 1
    except OSError:
        try:
            y = 2
        except ValueError:
            pass


def test_dis_try_except_as():
    print()
    print("=== try/except T as name ===")
    dis.dis(_try_except_as)


def test_dis_try_except_no_name():
    print()
    print("=== try/except T (no name) ===")
    dis.dis(_try_except_no_name)


def test_dis_try_except_multi():
    print()
    print("=== try/except with two handlers (both as name) ===")
    dis.dis(_try_except_multi_handler)


def _try_finally_inner():
    x = 1

def test_dis_try_finally():
    print()
    print("=== try/finally ===")
    dis.dis(_try_finally)
    print()
    print("=== plain function (no try) ===")
    dis.dis(_try_finally_inner)


def test_dis_nested():
    print()
    print("=== nested try/except inside except handler ===")
    dis.dis(_nested_try_except_in_except)
