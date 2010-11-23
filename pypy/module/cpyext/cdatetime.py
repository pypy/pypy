from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib.objectmodel import we_are_translated
from pypy.module.cpyext.pyobject import PyObject, make_ref, Py_DecRef
from pypy.module.cpyext.api import (
    cpython_api, CANNOT_FAIL, cpython_struct, PyObjectFields)
from pypy.module.cpyext.import_ import PyImport_Import
from pypy.module.cpyext.typeobject import PyTypeObjectPtr, render_immortal
from pypy.module.cpyext.state import State
from pypy.interpreter.error import OperationError
from pypy.tool.sourcetools import func_renamer

# API import function

PyDateTime_CAPI = cpython_struct(
    'PyDateTime_CAPI',
    (('DateType', PyTypeObjectPtr),
     ('DateTimeType', PyTypeObjectPtr),
     ('TimeType', PyTypeObjectPtr),
     ('DeltaType', PyTypeObjectPtr),
     ))

@cpython_api([], lltype.Ptr(PyDateTime_CAPI),
             error=lltype.nullptr(PyDateTime_CAPI))
def _PyDateTime_Import(space):
    datetimeAPI = lltype.malloc(PyDateTime_CAPI, flavor='raw',
                                track_allocation=False)

    if not we_are_translated():
        datetimeAPI_dealloc(space)
        space.fromcache(State).datetimeAPI = datetimeAPI

    w_datetime = PyImport_Import(space, space.wrap("datetime"))

    w_type = space.getattr(w_datetime, space.wrap("date"))
    datetimeAPI.c_DateType = rffi.cast(
        PyTypeObjectPtr, make_ref(space, w_type))
    render_immortal(datetimeAPI.c_DateType, w_type)

    w_type = space.getattr(w_datetime, space.wrap("datetime"))
    datetimeAPI.c_DateTimeType = rffi.cast(
        PyTypeObjectPtr, make_ref(space, w_type))
    render_immortal(datetimeAPI.c_DateTimeType, w_type)

    w_type = space.getattr(w_datetime, space.wrap("time"))
    datetimeAPI.c_TimeType = rffi.cast(
        PyTypeObjectPtr, make_ref(space, w_type))
    render_immortal(datetimeAPI.c_TimeType, w_type)

    w_type = space.getattr(w_datetime, space.wrap("timedelta"))
    datetimeAPI.c_DeltaType = rffi.cast(
        PyTypeObjectPtr, make_ref(space, w_type))
    render_immortal(datetimeAPI.c_DeltaType, w_type)

    return datetimeAPI

def datetimeAPI_dealloc(space):
    "Used in tests only, to please the refcount checker"
    if we_are_translated():
        return
    datetimeAPI = space.fromcache(State).datetimeAPI
    if datetimeAPI is None:
        return
    space.fromcache(State).datetimeAPI = None
    Py_DecRef(space, rffi.cast(PyObject, datetimeAPI.c_DateType))
    Py_DecRef(space, rffi.cast(PyObject, datetimeAPI.c_DateTimeType))
    Py_DecRef(space, rffi.cast(PyObject, datetimeAPI.c_TimeType))
    Py_DecRef(space, rffi.cast(PyObject, datetimeAPI.c_DeltaType))
    lltype.free(datetimeAPI, flavor='raw')

PyDateTime_Date = PyObject
PyDateTime_Time = PyObject
PyDateTime_DateTime = PyObject

PyDeltaObjectStruct = lltype.ForwardReference()
cpython_struct("PyDateTime_Delta", PyObjectFields, PyDeltaObjectStruct)
PyDateTime_Delta = lltype.Ptr(PyDeltaObjectStruct)

# Check functions

def make_check_function(func_name, type_name):
    @cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
    @func_renamer(func_name)
    def check(space, w_obj):
        try:
            return space.is_true(
                space.appexec([w_obj], """(obj):
                    from datetime import %s as datatype
                    return isinstance(obj, datatype)
                    """ % (type_name,)))
        except OperationError:
            return 0

    @cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
    @func_renamer(func_name + "Exact")
    def check_exact(space, w_obj):
        try:
            return space.is_true(
                space.appexec([w_obj], """(obj):
                    from datetime import %s as datatype
                    return type(obj) is datatype
                    """ % (type_name,)))
        except OperationError:
            return 0

make_check_function("PyDateTime_Check", "datetime")
make_check_function("PyDate_Check", "date")
make_check_function("PyTime_Check", "time")
make_check_function("PyDelta_Check", "timedelta")

# Constructors

@cpython_api([rffi.INT_real, rffi.INT_real, rffi.INT_real], PyObject)
def PyDate_FromDate(space, year, month, day):
    """Return a datetime.date object with the specified year, month and day.
    """
    year = rffi.cast(lltype.Signed, year)
    month = rffi.cast(lltype.Signed, month)
    day = rffi.cast(lltype.Signed, day)
    w_datetime = PyImport_Import(space, space.wrap("datetime"))
    return space.call_method(
        w_datetime, "date",
        space.wrap(year), space.wrap(month), space.wrap(day))

@cpython_api([rffi.INT_real, rffi.INT_real, rffi.INT_real, rffi.INT_real], PyObject)
def PyTime_FromTime(space, hour, minute, second, usecond):
    """Return a ``datetime.time`` object with the specified hour, minute, second and
    microsecond."""
    hour = rffi.cast(lltype.Signed, hour)
    minute = rffi.cast(lltype.Signed, minute)
    second = rffi.cast(lltype.Signed, second)
    usecond = rffi.cast(lltype.Signed, usecond)
    w_datetime = PyImport_Import(space, space.wrap("datetime"))
    return space.call_method(
        w_datetime, "time",
        space.wrap(hour), space.wrap(minute), space.wrap(second),
        space.wrap(usecond))

@cpython_api([rffi.INT_real, rffi.INT_real, rffi.INT_real, rffi.INT_real, rffi.INT_real, rffi.INT_real, rffi.INT_real], PyObject)
def PyDateTime_FromDateAndTime(space, year, month, day, hour, minute, second, usecond):
    """Return a datetime.datetime object with the specified year, month, day, hour,
    minute, second and microsecond.
    """
    year = rffi.cast(lltype.Signed, year)
    month = rffi.cast(lltype.Signed, month)
    day = rffi.cast(lltype.Signed, day)
    hour = rffi.cast(lltype.Signed, hour)
    minute = rffi.cast(lltype.Signed, minute)
    second = rffi.cast(lltype.Signed, second)
    usecond = rffi.cast(lltype.Signed, usecond)
    w_datetime = PyImport_Import(space, space.wrap("datetime"))
    return space.call_method(
        w_datetime, "datetime",
        space.wrap(year), space.wrap(month), space.wrap(day),
        space.wrap(hour), space.wrap(minute), space.wrap(second),
        space.wrap(usecond))
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyDateTime_FromTimestamp(space, w_args):
    """Create and return a new datetime.datetime object given an argument tuple
    suitable for passing to datetime.datetime.fromtimestamp().
    """
    w_datetime = PyImport_Import(space, space.wrap("datetime"))
    w_type = space.getattr(w_datetime, space.wrap("datetime"))
    w_method = space.getattr(w_type, space.wrap("fromtimestamp"))
    return space.call(w_method, w_args)

@cpython_api([PyObject], PyObject)
def PyDate_FromTimestamp(space, w_args):
    """Create and return a new datetime.date object given an argument tuple
    suitable for passing to datetime.date.fromtimestamp().
    """
    w_datetime = PyImport_Import(space, space.wrap("datetime"))
    w_type = space.getattr(w_datetime, space.wrap("date"))
    w_method = space.getattr(w_type, space.wrap("fromtimestamp"))
    return space.call(w_method, w_args)

@cpython_api([rffi.INT_real, rffi.INT_real, rffi.INT_real], PyObject)
def PyDelta_FromDSU(space, days, seconds, useconds):
    """Return a datetime.timedelta object representing the given number of days,
    seconds and microseconds.  Normalization is performed so that the resulting
    number of microseconds and seconds lie in the ranges documented for
    datetime.timedelta objects.
    """
    days = rffi.cast(lltype.Signed, days)
    seconds = rffi.cast(lltype.Signed, seconds)
    useconds = rffi.cast(lltype.Signed, useconds)
    w_datetime = PyImport_Import(space, space.wrap("datetime"))
    return space.call_method(
        w_datetime, "timedelta",
        space.wrap(days), space.wrap(seconds), space.wrap(useconds))

# Accessors

@cpython_api([PyDateTime_Date], rffi.INT_real, error=CANNOT_FAIL)
def PyDateTime_GET_YEAR(space, w_obj):
    """Return the year, as a positive int.
    """
    return space.getattr(w_obj, space.wrap("year"))

@cpython_api([PyDateTime_Date], rffi.INT_real, error=CANNOT_FAIL)
def PyDateTime_GET_MONTH(space, w_obj):
    """Return the month, as an int from 1 through 12.
    """
    return space.getattr(w_obj, space.wrap("month"))

@cpython_api([PyDateTime_Date], rffi.INT_real, error=CANNOT_FAIL)
def PyDateTime_GET_DAY(space, w_obj):
    """Return the day, as an int from 1 through 31.
    """
    return space.getattr(w_obj, space.wrap("day"))

@cpython_api([PyDateTime_DateTime], rffi.INT_real, error=CANNOT_FAIL)
def PyDateTime_DATE_GET_HOUR(space, w_obj):
    """Return the hour, as an int from 0 through 23.
    """
    return space.getattr(w_obj, space.wrap("hour"))

@cpython_api([PyDateTime_DateTime], rffi.INT_real, error=CANNOT_FAIL)
def PyDateTime_DATE_GET_MINUTE(space, w_obj):
    """Return the minute, as an int from 0 through 59.
    """
    return space.getattr(w_obj, space.wrap("minute"))

@cpython_api([PyDateTime_DateTime], rffi.INT_real, error=CANNOT_FAIL)
def PyDateTime_DATE_GET_SECOND(space, w_obj):
    """Return the second, as an int from 0 through 59.
    """
    return space.getattr(w_obj, space.wrap("second"))

@cpython_api([PyDateTime_DateTime], rffi.INT_real, error=CANNOT_FAIL)
def PyDateTime_DATE_GET_MICROSECOND(space, w_obj):
    """Return the microsecond, as an int from 0 through 999999.
    """
    return space.getattr(w_obj, space.wrap("microsecond"))

@cpython_api([PyDateTime_Time], rffi.INT_real, error=CANNOT_FAIL)
def PyDateTime_TIME_GET_HOUR(space, w_obj):
    """Return the hour, as an int from 0 through 23.
    """
    return space.getattr(w_obj, space.wrap("hour"))

@cpython_api([PyDateTime_Time], rffi.INT_real, error=CANNOT_FAIL)
def PyDateTime_TIME_GET_MINUTE(space, w_obj):
    """Return the minute, as an int from 0 through 59.
    """
    return space.getattr(w_obj, space.wrap("minute"))

@cpython_api([PyDateTime_Time], rffi.INT_real, error=CANNOT_FAIL)
def PyDateTime_TIME_GET_SECOND(space, w_obj):
    """Return the second, as an int from 0 through 59.
    """
    return space.getattr(w_obj, space.wrap("second"))

@cpython_api([PyDateTime_Time], rffi.INT_real, error=CANNOT_FAIL)
def PyDateTime_TIME_GET_MICROSECOND(space, w_obj):
    """Return the microsecond, as an int from 0 through 999999.
    """
    return space.getattr(w_obj, space.wrap("microsecond"))

# XXX these functions are not present in the Python API
# But it does not seem possible to expose a different structure
# for types defined in a python module like lib/datetime.py.

@cpython_api([PyDateTime_Delta], rffi.INT_real, error=CANNOT_FAIL)
def PyDateTime_DELTA_GET_DAYS(space, w_obj):
    return space.getattr(w_obj, space.wrap("days"))

@cpython_api([PyDateTime_Delta], rffi.INT_real, error=CANNOT_FAIL)
def PyDateTime_DELTA_GET_SECONDS(space, w_obj):
    return space.getattr(w_obj, space.wrap("seconds"))

@cpython_api([PyDateTime_Delta], rffi.INT_real, error=CANNOT_FAIL)
def PyDateTime_DELTA_GET_MICROSECONDS(space, w_obj):
    return space.getattr(w_obj, space.wrap("microseconds"))
