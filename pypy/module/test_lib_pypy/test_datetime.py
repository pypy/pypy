"""Additional tests for datetime."""

from __future__ import absolute_import
from lib_pypy import datetime
import py

def test_repr():
    print datetime
    expected = "datetime.datetime(1, 2, 3, 0, 0)"
    assert repr(datetime.datetime(1,2,3)) == expected

def test_attributes():
    for x in [datetime.date.today(),
              datetime.time(),
              datetime.datetime.utcnow(),
              datetime.timedelta(),
              datetime.tzinfo()]:
        raises(AttributeError, 'x.abc = 1')

def test_timedelta_init_long():
    td = datetime.timedelta(microseconds=20000000000000000000)
    assert td.days == 231481481
    assert td.seconds == 41600
    td = datetime.timedelta(microseconds=20000000000000000000.)
    assert td.days == 231481481
    assert td.seconds == 41600

def test_unpickle():
    e = raises(TypeError, datetime.date, '123')
    assert e.value.args[0] == 'an integer is required'
    e = raises(TypeError, datetime.time, '123')
    assert e.value.args[0] == 'an integer is required'
    e = raises(TypeError, datetime.datetime, '123')
    assert e.value.args[0] == 'an integer is required'

    datetime.time('\x01' * 6, None)
    with raises(TypeError) as e:
        datetime.time('\x01' * 6, 123)
    assert str(e.value) == "bad tzinfo state arg"

    datetime.datetime('\x01' * 10, None)
    with raises(TypeError) as e:
        datetime.datetime('\x01' * 10, 123)
    assert str(e.value) == "bad tzinfo state arg"

def test_strptime():
    import time, sys
    if sys.version_info < (2, 6):
        py.test.skip("needs the _strptime module")

    string = '2004-12-01 13:02:47'
    format = '%Y-%m-%d %H:%M:%S'
    expected = datetime.datetime(*(time.strptime(string, format)[0:6]))
    got = datetime.datetime.strptime(string, format)
    assert expected == got

def test_datetime_rounding():
    b = 0.0000001
    a = 0.9999994

    assert datetime.datetime.utcfromtimestamp(a).microsecond == 999999
    assert datetime.datetime.utcfromtimestamp(a).second == 0
    a += b
    assert datetime.datetime.utcfromtimestamp(a).microsecond == 999999
    assert datetime.datetime.utcfromtimestamp(a).second == 0
    a += b
    assert datetime.datetime.utcfromtimestamp(a).microsecond == 0
    assert datetime.datetime.utcfromtimestamp(a).second == 1

def test_more_datetime_rounding():
    # this test verified on top of CPython 2.7 (using a plain
    # "import datetime" above)
    expected_results = {
        -1000.0: 'datetime.datetime(1969, 12, 31, 23, 43, 20)',
        -999.9999996: 'datetime.datetime(1969, 12, 31, 23, 43, 20)',
        -999.4: 'datetime.datetime(1969, 12, 31, 23, 43, 20, 600000)',
        -999.0000004: 'datetime.datetime(1969, 12, 31, 23, 43, 21)',
        -1.0: 'datetime.datetime(1969, 12, 31, 23, 59, 59)',
        -0.9999996: 'datetime.datetime(1969, 12, 31, 23, 59, 59)',
        -0.4: 'datetime.datetime(1969, 12, 31, 23, 59, 59, 600000)',
        -0.0000004: 'datetime.datetime(1970, 1, 1, 0, 0)',
        0.0: 'datetime.datetime(1970, 1, 1, 0, 0)',
        0.0000004: 'datetime.datetime(1970, 1, 1, 0, 0)',
        0.4: 'datetime.datetime(1970, 1, 1, 0, 0, 0, 400000)',
        0.9999996: 'datetime.datetime(1970, 1, 1, 0, 0, 1)',
        1000.0: 'datetime.datetime(1970, 1, 1, 0, 16, 40)',
        1000.0000004: 'datetime.datetime(1970, 1, 1, 0, 16, 40)',
        1000.4: 'datetime.datetime(1970, 1, 1, 0, 16, 40, 400000)',
        1000.9999996: 'datetime.datetime(1970, 1, 1, 0, 16, 41)',
        1293843661.191: 'datetime.datetime(2011, 1, 1, 1, 1, 1, 191000)',
        }
    for t in sorted(expected_results):
        dt = datetime.datetime.utcfromtimestamp(t)
        assert repr(dt) == expected_results[t]

def test_utcfromtimestamp():
    """Confirm that utcfromtimestamp and fromtimestamp give consistent results.

    Based on danchr's test script in https://bugs.pypy.org/issue986
    """
    import os
    import time
    if os.name == 'nt':
        skip("setting os.environ['TZ'] ineffective on windows")
    try:
        prev_tz = os.environ.get("TZ")
        os.environ["TZ"] = "GMT"
        time.tzset()
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
        time.tzset()

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
    class Number:
        def __init__(self, value):
            self.value = value
        def __int__(self):
            return self.value

    for xx in [10L,
               decimal.Decimal(10),
               decimal.Decimal('10.9'),
               Number(10),
               Number(10L)]:
        assert datetime.datetime(10, 10, 10, 10, 10, 10, 10) == \
               datetime.datetime(xx, xx, xx, xx, xx, xx, xx)

    with py.test.raises(TypeError) as e:
        datetime.datetime(10, 10, '10')
    assert str(e.value) == 'an integer is required'

    f10 = Number(10.9)
    with py.test.raises(TypeError) as e:
        datetime.datetime(10, 10, f10)
    assert str(e.value) == '__int__ method should return an integer'

    class Float(float):
        pass
    s10 = Float(10.9)
    with py.test.raises(TypeError) as e:
        datetime.datetime(10, 10, s10)
    assert str(e.value) == 'integer argument expected, got float'

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
    import copy

    dt = datetime.datetime.utcnow()
    assert type(dt.microsecond) is int

    copy.copy(dt)

def test_radd():
    class X(object):
        def __radd__(self, other):
            return "radd"
    assert datetime.date(10, 10, 10) + X() == "radd"
