import pytest

from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.cdatetime import *
from pypy.module.cpyext.cdatetime import (
    _PyDateTime_Import, _PyDateTime_FromDateAndTime, _PyDate_FromDate,
    _PyTime_FromTime, _PyDelta_FromDelta, _PyTime_FromTimeAndFold,
    _PyDateTime_FromDateAndTimeAndFold)
from pypy.module.cpyext.pyobject import make_ref, decref
import datetime

def _get_date(space, w_obj):
    """year, month, day, as PyDateTime_GET_YEAR and friends read them"""
    py_obj = make_ref(space, w_obj)
    try:
        d = rffi.cast(PyDateTime_Date, py_obj).c_data
        return ((widen(d[0]) << 8) | widen(d[1]), widen(d[2]), widen(d[3]))
    finally:
        decref(space, py_obj)

def _get_time(space, w_obj, i):
    """hour, minute, second, microsecond; i is 0 for a time, 4 for a datetime"""
    py_obj = make_ref(space, w_obj)
    try:
        if i:
            d = rffi.cast(PyDateTime_DateTime, py_obj).c_data
        else:
            d = rffi.cast(PyDateTime_Time, py_obj).c_data
        usec = (widen(d[i + 3]) << 16) | (widen(d[i + 4]) << 8) | widen(d[i + 5])
        return (widen(d[i]), widen(d[i + 1]), widen(d[i + 2]), usec)
    finally:
        decref(space, py_obj)

def _get_delta(space, w_obj):
    py_obj = make_ref(space, w_obj)
    try:
        py_delta = rffi.cast(PyDateTime_Delta, py_obj)
        return (widen(py_delta.c_days), widen(py_delta.c_seconds),
                widen(py_delta.c_microseconds))
    finally:
        decref(space, py_obj)

class TestDatetime(BaseApiTest):
    def test_date(self, space):
        date_api = _PyDateTime_Import(space)
        w_date = _PyDate_FromDate(space, 2010, 6, 3, date_api.c_DateType)
        assert space.unwrap(space.str(w_date)) == '2010-06-03'

        assert PyDate_Check(space, w_date)
        assert PyDate_CheckExact(space, w_date)

        assert _get_date(space, w_date) == (2010, 6, 3)

    def test_time(self, space):
        date_api = _PyDateTime_Import(space)
        w_time = _PyTime_FromTime(
            space, 23, 15, 40, 123456, space.w_None, date_api.c_TimeType)
        assert space.unwrap(space.str(w_time)) == '23:15:40.123456'

        assert PyTime_Check(space, w_time)
        assert PyTime_CheckExact(space, w_time)

        assert _get_time(space, w_time, 0) == (23, 15, 40, 123456)

        w_time = _PyTime_FromTimeAndFold(
            space, 23, 15, 40, 123456, space.w_None, 0, date_api.c_TimeType)
        assert space.unwrap(space.str(w_time)) == '23:15:40.123456'

        assert PyTime_Check(space, w_time)
        assert PyTime_CheckExact(space, w_time)

        assert _get_time(space, w_time, 0) == (23, 15, 40, 123456)


    def test_datetime(self, space):
        date_api = _PyDateTime_Import(space)
        w_date = _PyDateTime_FromDateAndTime(
            space, 2010, 6, 3, 23, 15, 40, 123456, space.w_None,
            date_api.c_DateTimeType)
        assert space.unwrap(space.str(w_date)) == '2010-06-03 23:15:40.123456'

        assert PyDateTime_Check(space, w_date)
        assert PyDateTime_CheckExact(space, w_date)
        assert PyDate_Check(space, w_date)
        assert not PyDate_CheckExact(space, w_date)

        assert _get_date(space, w_date) == (2010, 6, 3)
        assert _get_time(space, w_date, 4) == (23, 15, 40, 123456)

        w_date = _PyDateTime_FromDateAndTimeAndFold(
            space, 2010, 6, 3, 23, 15, 40, 123456, space.w_None,
            0, date_api.c_DateTimeType)
        assert space.unwrap(space.str(w_date)) == '2010-06-03 23:15:40.123456'

        assert PyDateTime_Check(space, w_date)
        assert PyDateTime_CheckExact(space, w_date)
        assert PyDate_Check(space, w_date)
        assert not PyDate_CheckExact(space, w_date)

        assert _get_date(space, w_date) == (2010, 6, 3)
        assert _get_time(space, w_date, 4) == (23, 15, 40, 123456)

    def test_delta(self, space):
        date_api = _PyDateTime_Import(space)
        w_delta = space.appexec(
            [space.wrap(3), space.wrap(15)], """(days, seconds):
            from datetime import timedelta
            return timedelta(days, seconds)
        """)
        assert PyDelta_Check(space, w_delta)
        assert PyDelta_CheckExact(space, w_delta)

        w_delta = _PyDelta_FromDelta(space, 10, 20, 30, True, date_api.c_DeltaType)
        assert PyDelta_Check(space, w_delta)
        assert PyDelta_CheckExact(space, w_delta)

        assert _get_delta(space, w_delta) == (10, 20, 30)

    def test_accessor_functions(self, space):
        # kept exported for extensions built against older PyPy headers;
        # anything compiled against include/datetime.h uses the macros
        date_api = _PyDateTime_Import(space)
        w_date = _PyDate_FromDate(space, 2010, 6, 3, date_api.c_DateType)
        assert PyDateTime_GET_YEAR(space, w_date) == 2010
        assert PyDateTime_GET_MONTH(space, w_date) == 6
        assert PyDateTime_GET_DAY(space, w_date) == 3

        w_datetime = _PyDateTime_FromDateAndTime(
            space, 2010, 6, 3, 23, 15, 40, 123456, space.w_None,
            date_api.c_DateTimeType)
        assert PyDateTime_DATE_GET_HOUR(space, w_datetime) == 23
        assert PyDateTime_DATE_GET_MINUTE(space, w_datetime) == 15
        assert PyDateTime_DATE_GET_SECOND(space, w_datetime) == 40
        assert PyDateTime_DATE_GET_MICROSECOND(space, w_datetime) == 123456
        assert PyDateTime_GET_FOLD(space, w_datetime) == 0
        assert PyDateTime_DATE_GET_TZINFO(space, w_datetime) is space.w_None

        w_time = _PyTime_FromTime(
            space, 23, 15, 40, 123456, space.w_None, date_api.c_TimeType)
        assert PyDateTime_TIME_GET_HOUR(space, w_time) == 23
        assert PyDateTime_TIME_GET_MINUTE(space, w_time) == 15
        assert PyDateTime_TIME_GET_SECOND(space, w_time) == 40
        assert PyDateTime_TIME_GET_MICROSECOND(space, w_time) == 123456
        assert PyDateTime_TIME_GET_FOLD(space, w_time) == 0
        assert PyDateTime_TIME_GET_TZINFO(space, w_time) is space.w_None

        w_delta = _PyDelta_FromDelta(space, 10, 20, 30, True,
                                     date_api.c_DeltaType)
        assert PyDateTime_DELTA_GET_DAYS(space, w_delta) == 10
        assert PyDateTime_DELTA_GET_SECONDS(space, w_delta) == 20
        assert PyDateTime_DELTA_GET_MICROSECONDS(space, w_delta) == 30

    def test_fromtimestamp(self, space):
        w_args = space.wrap((0,))
        w_date = PyDate_FromTimestamp(space, w_args)
        date = datetime.date.fromtimestamp(0)
        assert space.unwrap(space.str(w_date)) == str(date)

        w_args = space.wrap((0,))
        w_date = PyDateTime_FromTimestamp(space, w_args)
        date = datetime.datetime.fromtimestamp(0)
        assert space.unwrap(space.str(w_date)) == str(date)

    @pytest.mark.parametrize('name', ['Time', 'DateTime', 'Date', 'Delta'])
    def test_basicsize(self, space, name):
        datetime = _PyDateTime_Import(space)
        py_size = getattr(datetime, "c_%sType" % name).c_tp_basicsize
        c_size = rffi.sizeof(cts.gettype("PyDateTime_%s" % name))
        assert py_size == c_size


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

    def test_capsule_import(self):
        # Simulate what a CPython-compiled extension's PyDateTime_IMPORT
        # macro actually does: PyCapsule_Import, not PyPy's own
        # _PyDateTime_Import rewrite.
        module = self.import_extension('foo', [
            ("get_types", "METH_NOARGS",
             """
                 PyDateTime_CAPI *capi = (PyDateTime_CAPI *)PyCapsule_Import(
                     "datetime.datetime_CAPI", 0);
                 if (!capi) {
                     return NULL;
                 }
                 return PyTuple_Pack(5,
                                     capi->DateType,
                                     capi->DateTimeType,
                                     capi->TimeType,
                                     capi->DeltaType,
                                     capi->TZInfoType);
             """),
            ("check", "METH_O",
             """
                 PyDateTimeAPI = (PyDateTime_CAPI *)PyCapsule_Import(
                     "datetime.datetime_CAPI", 0);
                 if (!PyDateTimeAPI) {
                     return NULL;
                 }
                 return Py_BuildValue("iiiii",
                     PyDate_Check(args), PyDate_CheckExact(args),
                     PyDateTime_Check(args), PyDateTime_CheckExact(args),
                     PyDelta_Check(args));
             """),
            ], prologue='#include "datetime.h"\n')
        import datetime
        assert module.get_types() == (datetime.date,
                                      datetime.datetime,
                                      datetime.time,
                                      datetime.timedelta,
                                      datetime.tzinfo)
        # real CPython PyDate_Check/PyDateTime_Check/... macros, driven by
        # the PyDateTimeAPI populated via PyCapsule_Import above.
        assert module.check(datetime.date(2020, 1, 1)) == (1, 1, 0, 0, 0)
        assert module.check(datetime.datetime(2020, 1, 1)) == (1, 0, 1, 1, 0)
        assert module.check(datetime.timedelta(1)) == (0, 0, 0, 0, 1)
        assert module.check(42) == (0, 0, 0, 0, 0)

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
            ("new_datetime_fromtimestamp", "METH_NOARGS",
             """ PyDateTime_IMPORT;
                 PyObject *ts = PyFloat_FromDouble(200000.0);
                 Py_INCREF(Py_None);
                 PyObject *tsargs = PyTuple_Pack(2, ts, Py_None);
                 PyObject *rv = PyDateTimeAPI->DateTime_FromTimestamp(
                    (PyObject *)PyDateTimeAPI->DateTimeType, tsargs, NULL);
                 Py_DECREF(tsargs);
                 return rv;
             """),
            ("new_dt_fromts_tzinfo", "METH_O",
             """ PyDateTime_IMPORT;
                 PyObject *ts = PyFloat_FromDouble(200000.0);
                 PyObject *tsargs = PyTuple_Pack(1, ts);
                 PyObject *tskwargs = PyDict_New();

                 Py_INCREF(args);
                 PyDict_SetItemString(tskwargs, "tz", args);
                 PyObject *rv = PyDateTimeAPI->DateTime_FromTimestamp(
                    (PyObject *)PyDateTimeAPI->DateTimeType, tsargs, tskwargs);
                 Py_DECREF(tsargs);
                 Py_DECREF(tskwargs);
                 return rv;
             """),
            ("new_date_fromtimestamp", "METH_NOARGS",
             """ PyDateTime_IMPORT;
                 PyObject *ts = PyFloat_FromDouble(1430366400.0);
                 Py_INCREF(Py_None);
                 PyObject *tsargs = PyTuple_Pack(1, ts);
                 PyObject *rv = PyDateTimeAPI->Date_FromTimestamp(
                    (PyObject *)PyDateTimeAPI->DateType, tsargs);
                 Py_DECREF(tsargs);
                 return rv;
             """),
        ], prologue='#include "datetime.h"\n')
        import datetime
        assert module.new_date() == datetime.date(2000, 6, 6)
        assert module.new_time() == datetime.time(6, 6, 6, 6)
        assert module.new_datetime() == datetime.datetime(
            2000, 6, 6, 6, 6, 6, 6)

        utc = datetime.timezone.utc

        # .fromtimestamp tests
        assert (module.new_datetime_fromtimestamp() ==
                datetime.datetime.fromtimestamp(200000.0))

        assert (module.new_dt_fromts_tzinfo(utc) ==
                datetime.datetime.fromtimestamp(200000.0, tz=utc))

        assert (module.new_date_fromtimestamp() ==
                datetime.date.fromtimestamp(1430366400.0))

    def test_timezone_constructors(self):
        # Testing that we can build timezones via the C api
        module = self.import_extension('foo', [
            ("new_timezone_fromoffset", "METH_NOARGS",
             """ PyDateTime_IMPORT;
                 PyObject *delta = PyDelta_FromDSU(0, 60 * 60, 0);
                 PyObject *tzinfo = PyTimeZone_FromOffset(delta);
                 Py_DECREF(delta);
                 return tzinfo;
             """),
            ("new_timezone_fromoffset_and_name", "METH_NOARGS",
             """ PyDateTime_IMPORT;
                 PyObject *delta = PyDelta_FromDSU(0, 60 * 60, 0);
                 PyObject *name = PyUnicode_FromString("spam");
                 PyObject *tzinfo = PyTimeZone_FromOffsetAndName(delta, name);
                 Py_DECREF(delta);
                 Py_DECREF(name);
                 return tzinfo;
             """),
            ("utc_singleton_access", "METH_NOARGS",
             """ PyDateTime_IMPORT;
                 Py_INCREF(PyDateTime_TimeZone_UTC);
                 return PyDateTime_TimeZone_UTC;
             """),
        ], prologue='#include "datetime.h"\n')
        import datetime

        one_hour = datetime.timedelta(hours=1)
        expected = datetime.timezone(one_hour)
        assert module.new_timezone_fromoffset() == expected

        expected = datetime.timezone(one_hour, "spam")
        assert module.new_timezone_fromoffset_and_name() == expected

        assert module.utc_singleton_access() == datetime.timezone.utc

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
                
#ifdef PYPY_VERSION
                 // PyPy keeps the name from PEP 495, issue 3627
                 PyDateTime_GET_FOLD(obj);
#endif
                 PyDateTime_DATE_GET_FOLD(obj);

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

    def test_get_macros(self):
        module = self.import_extension('foo', [
            ("get_date", "METH_O",
             """ PyDateTime_IMPORT;
                 return Py_BuildValue("iii", PyDateTime_GET_YEAR(args),
                                      PyDateTime_GET_MONTH(args),
                                      PyDateTime_GET_DAY(args));
             """),
            ("get_datetime", "METH_O",
             """ PyDateTime_IMPORT;
                 return Py_BuildValue("iiiiiiiiO",
                                      PyDateTime_GET_YEAR(args),
                                      PyDateTime_GET_MONTH(args),
                                      PyDateTime_GET_DAY(args),
                                      PyDateTime_DATE_GET_HOUR(args),
                                      PyDateTime_DATE_GET_MINUTE(args),
                                      PyDateTime_DATE_GET_SECOND(args),
                                      PyDateTime_DATE_GET_MICROSECOND(args),
                                      PyDateTime_DATE_GET_FOLD(args),
                                      PyDateTime_DATE_GET_TZINFO(args));
             """),
            ("get_time", "METH_O",
             """ PyDateTime_IMPORT;
                 return Py_BuildValue("iiiiiO",
                                      PyDateTime_TIME_GET_HOUR(args),
                                      PyDateTime_TIME_GET_MINUTE(args),
                                      PyDateTime_TIME_GET_SECOND(args),
                                      PyDateTime_TIME_GET_MICROSECOND(args),
                                      PyDateTime_TIME_GET_FOLD(args),
                                      PyDateTime_TIME_GET_TZINFO(args));
             """),
            ("get_delta", "METH_O",
             """ PyDateTime_IMPORT;
                 return Py_BuildValue("iii",
                                      PyDateTime_DELTA_GET_DAYS(args),
                                      PyDateTime_DELTA_GET_SECONDS(args),
                                      PyDateTime_DELTA_GET_MICROSECONDS(args));
             """),
            ("second_via_attr", "METH_O",
             """ /* like nanobind's limited-API datetime unpacking */
                 long v;
                 PyObject *w = PyObject_GetAttrString(args, "second");
                 if (w == NULL)
                     goto fail;
                 v = PyLong_AsLong(w);
                 Py_DECREF(w);
                 if (v == -1 && PyErr_Occurred())
                     goto fail;
                 return PyLong_FromLong(v);
             fail:
                 PyErr_Clear();
                 PyErr_SetString(PyExc_TypeError,
                                 "incompatible function arguments");
                 return NULL;
             """),
        ], prologue='#include "datetime.h"\n')
        from datetime import date, datetime, time, timedelta, timezone

        utc = timezone.utc
        assert module.get_date(date(2010, 6, 3)) == (2010, 6, 3)
        assert module.get_datetime(datetime(2010, 6, 3, 23, 15, 40, 123456)) == (
            2010, 6, 3, 23, 15, 40, 123456, 0, None)
        assert module.get_datetime(
            datetime(2010, 6, 3, 23, 15, 40, 123456, utc, fold=1)) == (
            2010, 6, 3, 23, 15, 40, 123456, 1, utc)
        assert module.get_time(time(23, 15, 40, 123456)) == (
            23, 15, 40, 123456, 0, None)
        assert module.get_time(time(23, 15, 40, 123456, utc, fold=1)) == (
            23, 15, 40, 123456, 1, utc)
        assert module.get_delta(timedelta(10, 20, 30)) == (10, 20, 30)

        # and the same for subclasses
        class MyDate(date):
            pass

        class MyDateTime(datetime):
            pass

        class MyTime(time):
            pass

        class MyDelta(timedelta):
            pass

        assert module.get_date(MyDate(2010, 6, 3)) == (2010, 6, 3)
        assert module.get_datetime(
            MyDateTime(2010, 6, 3, 23, 15, 40, 123456, utc)) == (
            2010, 6, 3, 23, 15, 40, 123456, 0, utc)
        assert module.get_time(MyTime(23, 15, 40, 123456)) == (
            23, 15, 40, 123456, 0, None)
        assert module.get_delta(MyDelta(10, 20, 30)) == (10, 20, 30)

        # properties that shadow the fields don't change what the macros
        # see, and converting the object to C doesn't call them: a bad value
        # is only an error for C code that does the attribute access itself
        class FakeTime(time):
            @property
            def second(self):
                return "hi"

        class FakeDateTime(datetime):
            @property
            def second(self):
                return "hi"

            @property
            def tzinfo(self):
                return "hi"

        fake_time = FakeTime(23, 15, 40, 123456)
        fake_datetime = FakeDateTime(2010, 6, 3, 23, 15, 40, 123456)
        assert module.get_time(fake_time) == (23, 15, 40, 123456, 0, None)
        assert module.get_datetime(fake_datetime) == (
            2010, 6, 3, 23, 15, 40, 123456, 0, None)
        for fake in (fake_time, fake_datetime):
            with raises(TypeError) as excinfo:
                module.second_via_attr(fake)
            assert str(excinfo.value) == "incompatible function arguments"
        assert module.second_via_attr(MyTime(23, 15, 40)) == 40

    def test_tzinfo(self):
        module = self.import_extension('foo', [
            ("time_with_tzinfo", "METH_O",
             """ PyDateTime_IMPORT;
                 return PyDateTimeAPI->Time_FromTime(
                    6, 6, 6, 6, args, PyDateTimeAPI->TimeType);
             """),
            ("datetime_with_tzinfo", "METH_O",
             """
                 PyObject * obj;
                 int tzrefcnt = args->ob_refcnt;
                 PyDateTime_IMPORT;
                 obj = PyDateTimeAPI->DateTime_FromDateAndTime(
                    2000, 6, 6, 6, 6, 6, 6, args,
                    PyDateTimeAPI->DateTimeType);
                if (!((PyDateTime_DateTime*)obj)->hastzinfo)
                {
                    Py_DECREF(obj);
                    PyErr_SetString(PyExc_ValueError, "missing tzinfo");
                    return NULL;
                }
                if (((PyDateTime_DateTime*)obj)->tzinfo->ob_refcnt <= tzrefcnt)
                {
                    Py_DECREF(obj);
                    PyErr_SetString(PyExc_ValueError, "tzinfo refcnt not incremented");
                    return NULL;
                }
                return obj;

             """),
            ("getrefcnt", "METH_O",
             """ return PyLong_FromSsize_t(args->ob_refcnt);
             """),
            ("read_tzinfo", "METH_O",
             """
                 PyObject * tz;
                 PyDateTime_IMPORT;
                 if (PyDateTime_Check(args)) {
                     PyDateTime_DateTime * o = (PyDateTime_DateTime *)args;
                     tz = o->hastzinfo ? o->tzinfo : Py_None;
                 }
                 else if (PyTime_Check(args)) {
                     PyDateTime_Time * o = (PyDateTime_Time *)args;
                     tz = o->hastzinfo ? o->tzinfo : Py_None;
                 }
                 else {
                     PyErr_SetString(PyExc_TypeError, "not a datetime or time");
                     return NULL;
                 }
                 Py_INCREF(tz);
                 return tz;
             """),
        ], prologue='#include "datetime.h"\n')
        from datetime import tzinfo, datetime, timedelta, time

        # copied from datetime documentation
        class GMT1(tzinfo):
            def __del__(self):
                print('deleting GMT1')
            def utcoffset(self, dt):
                return timedelta(hours=1) + self.dst(dt)
            def dst(self, dt):
                return timedelta(0)
            def tzname(self,dt):
                return "GMT +1"

        gmt1 = GMT1()
        dt1 = module.time_with_tzinfo(gmt1)
        assert dt1 == time(6, 6, 6, 6, gmt1)
        assert '+01' in str(dt1)
        dt_tz = module.datetime_with_tzinfo(gmt1)
        assert dt_tz == datetime(2000, 6, 6, 6, 6, 6, 6, gmt1)

        # the struct fields must be filled for subtypes too
        class MyDateTime(datetime):
            pass

        class MyTime(time):
            pass

        assert module.read_tzinfo(datetime(2000, 6, 6, tzinfo=gmt1)) is gmt1
        assert module.read_tzinfo(datetime(2000, 6, 6)) is None
        assert module.read_tzinfo(time(6, 6, tzinfo=gmt1)) is gmt1
        assert module.read_tzinfo(time(6, 6)) is None
        assert module.read_tzinfo(MyDateTime(2000, 6, 6, tzinfo=gmt1)) is gmt1
        assert module.read_tzinfo(MyDateTime(2000, 6, 6)) is None
        assert module.read_tzinfo(MyTime(6, 6, tzinfo=gmt1)) is gmt1
        assert module.read_tzinfo(MyTime(6, 6)) is None

        # and the reference stored there must be released again
        self.debug_collect()
        start = module.getrefcnt(gmt1)
        d = MyDateTime(2000, 6, 6, tzinfo=gmt1)
        assert module.read_tzinfo(d) is gmt1
        assert module.getrefcnt(gmt1) == start + 1
        del d
        self.debug_collect()
        assert module.getrefcnt(gmt1) == start

    def test_checks(self):
        module = self.import_extension('foo', [
            ("checks", "METH_O",
             """ PyDateTime_IMPORT;
                 return PyTuple_Pack(10,
                    PyBool_FromLong(PyDateTime_Check(args)),
                    PyBool_FromLong(PyDateTime_CheckExact(args)),
                    PyBool_FromLong(PyDate_Check(args)),
                    PyBool_FromLong(PyDate_CheckExact(args)),
                    PyBool_FromLong(PyTime_Check(args)),
                    PyBool_FromLong(PyTime_CheckExact(args)),
                    PyBool_FromLong(PyDelta_Check(args)),
                    PyBool_FromLong(PyDelta_CheckExact(args)),
                    PyBool_FromLong(PyTZInfo_Check(args)),
                    PyBool_FromLong(PyTZInfo_CheckExact(args))
                );
             """),
        ], prologue='#include "datetime.h"\n')
        from datetime import tzinfo, datetime, timedelta, time, date
        o = date(1, 1, 1)
        assert module.checks(o) == (False,) * 2 + (True,) * 2 + (False,) * 6
        o = time(1, 1, 1)
        assert module.checks(o) == (False,) * 4 + (True,) * 2 + (False,) * 4
        o = timedelta(1, 1, 1)
        assert module.checks(o) == (False,) * 6 + (True,) * 2 + (False,) * 2
        o = datetime(1, 1, 1)
        assert module.checks(o) == (True,) * 3 + (False,) * 7 # isinstance(datetime, date)
        o = tzinfo()
        assert module.checks(o) == (False,) * 8 + (True,) * 2

    def test_misc(self):
        # Taken from the cython time_pxd.pyx test_time() test
        module = self.import_extension('foo', [
            ("getsystemclock", "METH_NOARGS",
             """ PyDateTime_IMPORT;
                _PyTime_t tic = _PyTime_GetSystemClock();
                double r = _PyTime_AsSecondsDouble(tic);
                return PyFloat_FromDouble(r);
            """),
            ("get_qualname", "METH_NOARGS",
            """
                return PyType_GetQualName(PyDateTimeAPI->DateType);
            """),
        ], prologue='#include "datetime.h"\n')
        import time
        # warm up the time.time function
        for _ in range(2000):
            tic1 = time.time()
        tic2 = module.getsystemclock()
        tic3 = time.time()
        assert tic1 <= tic2, "%s, %s" % (tic1, tic2)
        assert tic2 <= tic3, "%s, %s" % (tic2, tic3)
        assert module.get_qualname() == "date"
