from __future__ import absolute_import
import py

from lib_pypy import datetime

def test_repr():
    print datetime
    expected = "datetime.datetime(1, 2, 3, 0, 0)"
    assert repr(datetime.datetime(1,2,3)) == expected

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
        -1000.0: 'datetime.datetime(1970, 1, 1, 0, 43, 20)',
        -999.9999996: 'datetime.datetime(1970, 1, 1, 0, 43, 20)',
        -999.4: 'datetime.datetime(1970, 1, 1, 0, 43, 20, 600000)',
        -999.0000004: 'datetime.datetime(1970, 1, 1, 0, 43, 21)',
        -1.0: 'datetime.datetime(1970, 1, 1, 0, 59, 59)',
        -0.9999996: 'datetime.datetime(1970, 1, 1, 0, 59, 59)',
        -0.4: 'datetime.datetime(1970, 1, 1, 0, 59, 59, 600000)',
        -0.0000004: 'datetime.datetime(1970, 1, 1, 1, 0)',
        0.0: 'datetime.datetime(1970, 1, 1, 1, 0)',
        0.0000004: 'datetime.datetime(1970, 1, 1, 1, 0)',
        0.4: 'datetime.datetime(1970, 1, 1, 1, 0, 0, 400000)',
        0.9999996: 'datetime.datetime(1970, 1, 1, 1, 0, 1)',
        1000.0: 'datetime.datetime(1970, 1, 1, 1, 16, 40)',
        1000.0000004: 'datetime.datetime(1970, 1, 1, 1, 16, 40)',
        1000.4: 'datetime.datetime(1970, 1, 1, 1, 16, 40, 400000)',
        1000.9999996: 'datetime.datetime(1970, 1, 1, 1, 16, 41)',
        1293843661.191: 'datetime.datetime(2011, 1, 1, 2, 1, 1, 191000)',
        }
    for t in sorted(expected_results):
        dt = datetime.datetime.fromtimestamp(t)
        assert repr(dt) == expected_results[t]
