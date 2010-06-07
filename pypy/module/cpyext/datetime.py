from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.pyobject import PyObject
from pypy.module.cpyext.api import cpython_api, CANNOT_FAIL
from pypy.module.cpyext.import_ import PyImport_Import

@cpython_api([], lltype.Void)
def PyDateTime_IMPORT(space):
    return

@cpython_api([rffi.INT, rffi.INT, rffi.INT, rffi.INT], PyObject)
def PyTime_FromTime(space, hour, minute, second, usecond):
    w_datetime = PyImport_Import(space, space.wrap("datetime"))
    return space.call_method(
        w_datetime, "time",
        space.wrap(hour), space.wrap(minute), space.wrap(second),
        space.wrap(usecond))

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyDelta_Check(space, w_obj):
    """Return true if ob is of type PyDateTime_DeltaType or a subtype of
    PyDateTime_DeltaType.  ob must not be NULL.
    """
    return space.is_true(
        space.appexec([w_obj], """(obj):
                                    from datetime import timedelta
                                    return isinstance(obj, timedelta)
                      """))
