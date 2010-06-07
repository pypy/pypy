from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.test.test_api import BaseApiTest

class TestDatetime(BaseApiTest):
    def test_date(self, space, api):
        w_date = api.PyDate_FromDate(2010, 06, 03)
        assert space.unwrap(space.str(w_date)) == '2010-06-03'

        assert api.PyDate_Check(w_date)
        assert api.PyDate_CheckExact(w_date)

        assert space.unwrap(space.newtuple([
            api.PyDateTime_GET_YEAR(w_date),
            api.PyDateTime_GET_MONTH(w_date),
            api.PyDateTime_GET_DAY(w_date)])) == (
            2010, 06, 03)

    def test_time(self, space, api):
        w_time = api.PyTime_FromTime(23, 15, 40, 123456)
        assert space.unwrap(space.str(w_time)) == '23:15:40.123456'

        assert api.PyTime_Check(w_time)
        assert api.PyTime_CheckExact(w_time)

        assert space.unwrap(space.newtuple([
            api.PyDateTime_TIME_GET_HOUR(w_time),
            api.PyDateTime_TIME_GET_MINUTE(w_time),
            api.PyDateTime_TIME_GET_SECOND(w_time),
            api.PyDateTime_TIME_GET_MICROSECOND(w_time)])) == (
            23, 15, 40, 123456)

    def test_datetime(self, space, api):
        w_date = api.PyDateTime_FromDateAndTime(
            2010, 06, 03, 23, 15, 40, 123456)
        assert space.unwrap(space.str(w_date)) == '2010-06-03 23:15:40.123456'

        assert api.PyDateTime_Check(w_date)
        assert api.PyDateTime_CheckExact(w_date)
        assert api.PyDate_Check(w_date)
        assert not api.PyDate_CheckExact(w_date)

        assert space.unwrap(space.newtuple([
            api.PyDateTime_GET_YEAR(w_date),
            api.PyDateTime_GET_MONTH(w_date),
            api.PyDateTime_GET_DAY(w_date),
            api.PyDateTime_DATE_GET_HOUR(w_date),
            api.PyDateTime_DATE_GET_MINUTE(w_date),
            api.PyDateTime_DATE_GET_SECOND(w_date),
            api.PyDateTime_DATE_GET_MICROSECOND(w_date)])) == (
            2010, 06, 03, 23, 15, 40, 123456)

    def test_delta(self, space, api):
        w_delta = space.appexec(
            [space.wrap(3), space.wrap(15)], """(days, seconds):
            from datetime import timedelta
            return timedelta(days, seconds)
        """)
        assert api.PyDelta_Check(w_delta)
        assert api.PyDelta_CheckExact(w_delta)

        w_delta = api.PyDelta_FromDSU(10, 20, 30)
        assert api.PyDelta_Check(w_delta)
        assert api.PyDelta_CheckExact(w_delta)
