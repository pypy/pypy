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

    
