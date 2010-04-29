from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.pyobject import PyObject
from pypy.module.cpyext.api import cpython_api
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
