from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.test.test_api import BaseApiTest
import datetime

class TestDatetime(BaseApiTest):
    def test_date(self, space, api):
        w_date = api.PyDate_FromDate(2010, 06, 03)
        assert space.unwrap(space.str(w_date)) == '2010-06-03'

        assert api.PyDate_Check(w_date)
        assert api.PyDate_CheckExact(w_date)

        assert api.PyDateTime_GET_YEAR(w_date) == 2010
        assert api.PyDateTime_GET_MONTH(w_date) == 6
        assert api.PyDateTime_GET_DAY(w_date) == 3

    def test_time(self, space, api):
        w_time = api.PyTime_FromTime(23, 15, 40, 123456)
        assert space.unwrap(space.str(w_time)) == '23:15:40.123456'

        assert api.PyTime_Check(w_time)
        assert api.PyTime_CheckExact(w_time)

        assert api.PyDateTime_TIME_GET_HOUR(w_time) == 23
        assert api.PyDateTime_TIME_GET_MINUTE(w_time) == 15
        assert api.PyDateTime_TIME_GET_SECOND(w_time) == 40
        assert api.PyDateTime_TIME_GET_MICROSECOND(w_time) == 123456

    def test_datetime(self, space, api):
        w_date = api.PyDateTime_FromDateAndTime(
            2010, 06, 03, 23, 15, 40, 123456)
        assert space.unwrap(space.str(w_date)) == '2010-06-03 23:15:40.123456'

        assert api.PyDateTime_Check(w_date)
        assert api.PyDateTime_CheckExact(w_date)
        assert api.PyDate_Check(w_date)
        assert not api.PyDate_CheckExact(w_date)

        assert api.PyDateTime_GET_YEAR(w_date) == 2010
        assert api.PyDateTime_GET_MONTH(w_date) == 6
        assert api.PyDateTime_GET_DAY(w_date) == 3
        assert api.PyDateTime_DATE_GET_HOUR(w_date) == 23
        assert api.PyDateTime_DATE_GET_MINUTE(w_date) == 15
        assert api.PyDateTime_DATE_GET_SECOND(w_date) == 40
        assert api.PyDateTime_DATE_GET_MICROSECOND(w_date) == 123456

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

        assert api.PyDateTime_DELTA_GET_DAYS(w_delta) == 10
        assert api.PyDateTime_DELTA_GET_SECONDS(w_delta) == 20
        assert api.PyDateTime_DELTA_GET_MICROSECONDS(w_delta) == 30

    def test_fromtimestamp(self, space, api):
        w_args = space.wrap((0,))
        w_date = api.PyDate_FromTimestamp(w_args)
        date = datetime.date.fromtimestamp(0)
        assert space.unwrap(space.str(w_date)) == str(date)

        w_args = space.wrap((0,))
        w_date = api.PyDateTime_FromTimestamp(w_args)
        date = datetime.datetime.fromtimestamp(0)
        assert space.unwrap(space.str(w_date)) == str(date)

class AppTestDatetime(AppTestCpythonExtensionBase):
    def test_CAPI(self):
        module = self.import_extension('foo', [
            ("get_types", "METH_NOARGS",
             """
                 PyDateTime_IMPORT;
                 return PyTuple_Pack(4,
                                     PyDateTimeAPI->DateType,
                                     PyDateTimeAPI->DateTimeType,
                                     PyDateTimeAPI->TimeType,
                                     PyDateTimeAPI->DeltaType);
             """),
            ("clear_types", "METH_NOARGS",
             """
                 Py_DECREF(PyDateTimeAPI->DateType);
                 Py_DECREF(PyDateTimeAPI->DateTimeType);
                 Py_DECREF(PyDateTimeAPI->TimeType);
                 Py_DECREF(PyDateTimeAPI->DeltaType);
                 Py_RETURN_NONE;
             """
             )
            ])
        import datetime
        assert module.get_types() == (datetime.date,
                                      datetime.datetime,
                                      datetime.time,
                                      datetime.timedelta)
        module.clear_types()
