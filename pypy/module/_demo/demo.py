from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.rpython.rctypes.tool import ctypes_platform
import sys
from ctypes import *

# __________ the standard C library __________

# LoadLibrary is deprecated in ctypes, this should be removed at some point
if "load" in dir(cdll):
    cdll_load = cdll.load
else:
    cdll_load = cdll.LoadLibrary

if sys.platform == 'win32':
    mylib = cdll_load('msvcrt.dll')
elif sys.platform == 'linux2':
    mylib = cdll_load('libc.so.6')
elif sys.platform == 'darwin':
    mylib = cdll.c
else:
    py.test.skip("don't know how to load the c lib for %s" % 
            sys.platform)
# ____________________________________________


time_t = ctypes_platform.getsimpletype('time_t', '#include <time.h>', c_long)

time = mylib.time
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
