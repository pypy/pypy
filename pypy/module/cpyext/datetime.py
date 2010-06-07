from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.pyobject import PyObject
from pypy.module.cpyext.api import cpython_api, CANNOT_FAIL
from pypy.module.cpyext.import_ import PyImport_Import
from pypy.interpreter.error import OperationError
from pypy.tool.sourcetools import func_renamer

@cpython_api([], lltype.Void)
def PyDateTime_IMPORT(space):
    return

PyDateTime_Date = PyObject
PyDateTime_Time = PyObject
PyDateTime_DateTime = PyObject

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
    w_datetime = PyImport_Import(space, space.wrap("datetime"))
    return space.call_method(
        w_datetime, "date",
        space.wrap(year), space.wrap(month), space.wrap(day))

@cpython_api([rffi.INT_real, rffi.INT_real, rffi.INT_real, rffi.INT_real], PyObject)
def PyTime_FromTime(space, hour, minute, second, usecond):
    """Return a ``datetime.time`` object with the specified hour, minute, second and
    microsecond."""
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
