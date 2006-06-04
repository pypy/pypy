from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.rpython.rctypes.tool import ctypes_platform
from pypy.rpython.rctypes.tool.libc import libc
import sys
from ctypes import *

time_t = ctypes_platform.getsimpletype('time_t', '#include <time.h>', c_long)

time = libc.time
time.argtypes = [POINTER(time_t)]
time.restype = time_t

def get(space, name):
    w_module = space.getbuiltinmodule('_demo')
    return space.getattr(w_module, space.wrap(name))


def measuretime(space, repetitions, w_callable):
    if repetitions <= 0:
        w_DemoError = get(space, 'DemoError')
        msg = "repetition count must be > 0"
        raise OperationError(w_DemoError, space.wrap(msg))
    starttime = time(None)
    for i in range(repetitions):
        space.call_function(w_callable)
    endtime = time(None)
    return space.wrap(endtime - starttime)
measuretime.unwrap_spec = [ObjSpace, int, W_Root]
