"""Additional tests for datetime."""

import py

import time
from lib_pypy import datetime
import copy
import os

def test_utcfromtimestamp():
    """Confirm that utcfromtimestamp and fromtimestamp give consistent results.

    Based on danchr's test script in https://bugs.pypy.org/issue986
    """
    try:
        prev_tz = os.environ.get("TZ")
        os.environ["TZ"] = "GMT"
        for unused in xrange(100):
            now = time.time()
            delta = (datetime.datetime.utcfromtimestamp(now) -
                     datetime.datetime.fromtimestamp(now))
            assert delta.days * 86400 + delta.seconds == 0
    finally:
        if prev_tz is None:
            del os.environ["TZ"]
        else:
            os.environ["TZ"] = prev_tz

def test_utcfromtimestamp_microsecond():
    dt = datetime.datetime.utcfromtimestamp(0)
    assert isinstance(dt.microsecond, int)

def test_default_args():
    with py.test.raises(TypeError):
        datetime.datetime()
    with py.test.raises(TypeError):
        datetime.datetime(10)
    with py.test.raises(TypeError):
        datetime.datetime(10, 10)
    datetime.datetime(10, 10, 10)

def test_check_arg_types():
    import decimal
    i10 = 10
    l10 = 10L
    d10 = decimal.Decimal(10)
    d11 = decimal.Decimal(10.9)
    class C10:
        def __int__(self):
            return 10
    c10 = C10()
    assert datetime.datetime(i10, i10, i10, i10, i10, i10, i10) == \
           datetime.datetime(l10, l10, l10, l10, l10, l10, l10) == \
           datetime.datetime(d10, d10, d10, d10, d10, d10, d10) == \
           datetime.datetime(d11, d11, d11, d11, d11, d11, d11) == \
           datetime.datetime(c10, c10, c10, c10, c10, c10, c10)

    with py.test.raises(TypeError):
        datetime.datetime(10, '10', 10)

    class S10(float):
        pass
    s10 = S10(10.9)
    with py.test.raises(TypeError):
        datetime.datetime(10, s10, 10)

    class F10:
        def __int__(self):
            return 10.9
    f10 = F10()
    with py.test.raises(TypeError):
        datetime.datetime(10, f10, 10)

    with py.test.raises(TypeError):
        datetime.datetime(10., 10, 10)
    with py.test.raises(TypeError):
        datetime.datetime(10, 10., 10)
    with py.test.raises(TypeError):
        datetime.datetime(10, 10, 10.)
    with py.test.raises(TypeError):
        datetime.datetime(10, 10, 10, 10.)
    with py.test.raises(TypeError):
        datetime.datetime(10, 10, 10, 10, 10.)
    with py.test.raises(TypeError):
        datetime.datetime(10, 10, 10, 10, 10, 10.)
    with py.test.raises(TypeError):
        datetime.datetime(10, 10, 10, 10, 10, 10, 10.)

def test_utcnow_microsecond():
    dt = datetime.datetime.utcnow()
    assert type(dt.microsecond) is int

    copy.copy(dt)

def test_radd():
    class X(object):
        def __radd__(self, other):
            return "radd"
    assert datetime.date(10, 10, 10) + X() == "radd"
