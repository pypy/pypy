"""Additional tests for datetime."""

import py

import time
import datetime
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


def test_integer_args():
    with py.test.raises(TypeError):
        datetime.datetime(10, 10, 10.)
    with py.test.raises(TypeError):
        datetime.datetime(10, 10, 10, 10, 10.)
    with py.test.raises(TypeError):
        datetime.datetime(10, 10, 10, 10, 10, 10.)

def test_utcnow_microsecond():
    dt = datetime.datetime.utcnow()
    assert type(dt.microsecond) is int

    copy.copy(dt)