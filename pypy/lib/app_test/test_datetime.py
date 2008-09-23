
import datetime

def test_repr():
    print datetime
    expected = "datetime.datetime(1, 2, 3, 0, 0)"
    assert repr(datetime.datetime(1,2,3)) == expected
