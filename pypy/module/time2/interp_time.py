from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.rpython.rctypes.tool import ctypes_platform
from pypy.rpython.rctypes.tool.libc import libc

import sys
from ctypes import *

class CConfig:
    _header_ = """#include <time.h>
"""
    time_t = ctypes_platform.SimpleType('time_t', c_int)
    clock_t = ctypes_platform.SimpleType('clock_t', c_int)
    CLOCKS_PER_SEC = ctypes_platform.DefinedConstantInteger('CLOCKS_PER_SEC')

cconfig = ctypes_platform.configure(CConfig)

clock_t = cconfig['clock_t']
CLOCKS_PER_SEC = cconfig['CLOCKS_PER_SEC']

c_clock = libc.clock 
c_clock.restype = clock_t 

def clock(space):
    return space.wrap(float(c_clock()) / CLOCKS_PER_SEC)
clock.unwrap_spec = [ObjSpace, ]
