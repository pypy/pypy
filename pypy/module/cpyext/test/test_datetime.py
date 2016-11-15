from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.test.test_api import BaseApiTest
import datetime

class TestDatetime(BaseApiTest):
    def test_date(self, space, api):
        date_api = api._PyDateTime_Import()
        w_date = api._PyDate_FromDate(2010, 06, 03, date_api.c_DateType)
        assert space.unwrap(space.str(w_date)) == '2010-06-03'

        assert api.PyDate_Check(w_date)
        assert api.PyDate_CheckExact(w_date)

        assert api.PyDateTime_GET_YEAR(w_date) == 2010
        assert api.PyDateTime_GET_MONTH(w_date) == 6
        assert api.PyDateTime_GET_DAY(w_date) == 3

    def test_time(self, space, api):
        date_api = api._PyDateTime_Import()
        w_time = api._PyTime_FromTime(23, 15, 40, 123456,
                                      space.w_None, date_api.c_TimeType)
        assert space.unwrap(space.str(w_time)) == '23:15:40.123456'

        assert api.PyTime_Check(w_time)
        assert api.PyTime_CheckExact(w_time)

        assert api.PyDateTime_TIME_GET_HOUR(w_time) == 23
        assert api.PyDateTime_TIME_GET_MINUTE(w_time) == 15
        assert api.PyDateTime_TIME_GET_SECOND(w_time) == 40
        assert api.PyDateTime_TIME_GET_MICROSECOND(w_time) == 123456

    def test_datetime(self, space, api):
        date_api = api._PyDateTime_Import()
        w_date = api._PyDateTime_FromDateAndTime(
            2010, 06, 03, 23, 15, 40, 123456,
            space.w_None, date_api.c_DateTimeType)
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
        date_api = api._PyDateTime_Import()
        w_delta = space.appexec(
            [space.wrap(3), space.wrap(15)], """(days, seconds):
            from datetime import timedelta
            return timedelta(days, seconds)
        """)
        assert api.PyDelta_Check(w_delta)
        assert api.PyDelta_CheckExact(w_delta)

        w_delta = api._PyDelta_FromDelta(10, 20, 30, True, date_api.c_DeltaType)
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

    def test_tzinfo(self, space, api):
        w_tzinfo = space.appexec(
            [], """():
            from datetime import tzinfo
            return tzinfo()
        """)
        assert api.PyTZInfo_Check(w_tzinfo)
        assert api.PyTZInfo_CheckExact(w_tzinfo)
        assert not api.PyTZInfo_Check(space.w_None)

class AppTestDatetime(AppTestCpythonExtensionBase):
    def test_CAPI(self):
        module = self.import_extension('foo', [
            ("get_types", "METH_NOARGS",
             """
                 PyDateTime_IMPORT;
                 if (!PyDateTimeAPI) {
                     PyErr_SetString(PyExc_RuntimeError, "No PyDateTimeAPI");
                     return NULL;
                 }
                 return PyTuple_Pack(5,
                                     PyDateTimeAPI->DateType,
                                     PyDateTimeAPI->DateTimeType,
                                     PyDateTimeAPI->TimeType,
                                     PyDateTimeAPI->DeltaType,
                                     PyDateTimeAPI->TZInfoType);
             """),
            ("clear_types", "METH_NOARGS",
             """
                 Py_DECREF(PyDateTimeAPI->DateType);
                 Py_DECREF(PyDateTimeAPI->DateTimeType);
                 Py_DECREF(PyDateTimeAPI->TimeType);
                 Py_DECREF(PyDateTimeAPI->DeltaType);
                 Py_DECREF(PyDateTimeAPI->TZInfoType);
                 Py_RETURN_NONE;
             """
             )
            ], prologue='#include "datetime.h"\n')
        import datetime
        assert module.get_types() == (datetime.date,
                                      datetime.datetime,
                                      datetime.time,
                                      datetime.timedelta,
                                      datetime.tzinfo)
        module.clear_types()

    def test_constructors(self):
        module = self.import_extension('foo', [
            ("new_date", "METH_NOARGS",
             """ PyDateTime_IMPORT;
                 return PyDateTimeAPI->Date_FromDate(
                    2000, 6, 6, PyDateTimeAPI->DateType);
             """),
            ("new_time", "METH_NOARGS",
             """ PyDateTime_IMPORT;
                 return PyDateTimeAPI->Time_FromTime(
                    6, 6, 6, 6, Py_None, PyDateTimeAPI->TimeType);
             """),
            ("new_datetime", "METH_NOARGS",
             """ PyDateTime_IMPORT;
                 return PyDateTimeAPI->DateTime_FromDateAndTime(
                    2000, 6, 6, 6, 6, 6, 6, Py_None,
                    PyDateTimeAPI->DateTimeType);
             """),
        ], prologue='#include "datetime.h"\n')
        import datetime
        assert module.new_date() == datetime.date(2000, 6, 6)
        assert module.new_time() == datetime.time(6, 6, 6, 6)
        assert module.new_datetime() == datetime.datetime(
            2000, 6, 6, 6, 6, 6, 6)

    def test_macros(self):
        module = self.import_extension('foo', [
            ("test_date_macros", "METH_NOARGS",
             """
                 PyObject* obj;
                 PyDateTime_Date* d;
                 PyDateTime_IMPORT;
                 if (!PyDateTimeAPI) {
                     PyErr_SetString(PyExc_RuntimeError, "No PyDateTimeAPI");
                     return NULL;
                 }
                 obj = PyDate_FromDate(2000, 6, 6);
                 d = (PyDateTime_Date*)obj;

                 PyDateTime_GET_YEAR(obj);
                 PyDateTime_GET_YEAR(d);

                 PyDateTime_GET_MONTH(obj);
                 PyDateTime_GET_MONTH(d);

                 PyDateTime_GET_DAY(obj);
                 PyDateTime_GET_DAY(d);

                 return obj;
             """),
            ("test_datetime_macros", "METH_NOARGS",
             """
                 PyObject* obj;
                 PyDateTime_DateTime *dt;
                 PyDateTime_IMPORT;
                 if (!PyDateTimeAPI) {
                     PyErr_SetString(PyExc_RuntimeError, "No PyDateTimeAPI");
                     return NULL;
                 }
                 obj = PyDateTime_FromDateAndTime(2000, 6, 6, 6, 6, 6, 6);
                 dt = (PyDateTime_DateTime*)obj;

                 PyDateTime_GET_YEAR(obj);
                 PyDateTime_GET_YEAR(dt);

                 PyDateTime_GET_MONTH(obj);
                 PyDateTime_GET_MONTH(dt);

                 PyDateTime_GET_DAY(obj);
                 PyDateTime_GET_DAY(dt);

                 PyDateTime_DATE_GET_HOUR(obj);
                 PyDateTime_DATE_GET_HOUR(dt);

                 PyDateTime_DATE_GET_MINUTE(obj);
                 PyDateTime_DATE_GET_MINUTE(dt);

                 PyDateTime_DATE_GET_SECOND(obj);
                 PyDateTime_DATE_GET_SECOND(dt);

                 PyDateTime_DATE_GET_MICROSECOND(obj);
                 PyDateTime_DATE_GET_MICROSECOND(dt);

                 return obj;
             """),
            ("test_time_macros", "METH_NOARGS",
             """
                 PyObject* obj;
                 PyDateTime_Time* t;
                 PyDateTime_IMPORT;
                 if (!PyDateTimeAPI) {
                     PyErr_SetString(PyExc_RuntimeError, "No PyDateTimeAPI");
                     return NULL;
                 }
                 obj = PyTime_FromTime(6, 6, 6, 6);
                 t = (PyDateTime_Time*)obj;

                 PyDateTime_TIME_GET_HOUR(obj);
                 PyDateTime_TIME_GET_HOUR(t);

                 PyDateTime_TIME_GET_MINUTE(obj);
                 PyDateTime_TIME_GET_MINUTE(t);

                 PyDateTime_TIME_GET_SECOND(obj);
                 PyDateTime_TIME_GET_SECOND(t);

                 PyDateTime_TIME_GET_MICROSECOND(obj);
                 PyDateTime_TIME_GET_MICROSECOND(t);

                 return obj;
             """),
            ("test_delta_macros", "METH_NOARGS",
             """
                 PyObject* obj;
                 PyDateTime_Delta* delta;
                 PyDateTime_IMPORT;
                 if (!PyDateTimeAPI) {
                     PyErr_SetString(PyExc_RuntimeError, "No PyDateTimeAPI");
                     return NULL;
                 }
                 obj = PyDelta_FromDSU(6, 6, 6);
                 delta = (PyDateTime_Delta*)obj;

#if defined(PYPY_VERSION) || PY_VERSION_HEX >= 0x03030000
                 // These macros are only defined in CPython 3.x and PyPy.
                 // See: http://bugs.python.org/issue13727
                 PyDateTime_DELTA_GET_DAYS(obj);
                 PyDateTime_DELTA_GET_DAYS(delta);

                 PyDateTime_DELTA_GET_SECONDS(obj);
                 PyDateTime_DELTA_GET_SECONDS(delta);

                 PyDateTime_DELTA_GET_MICROSECONDS(obj);
                 PyDateTime_DELTA_GET_MICROSECONDS(delta);
#endif
                 return obj;
             """),
            ], prologue='#include "datetime.h"\n')
        import datetime
        assert module.test_date_macros() == datetime.date(2000, 6, 6)
        assert module.test_datetime_macros() == datetime.datetime(
            2000, 6, 6, 6, 6, 6, 6)
        assert module.test_time_macros() == datetime.time(6, 6, 6, 6)
        assert module.test_delta_macros() == datetime.timedelta(6, 6, 6)
