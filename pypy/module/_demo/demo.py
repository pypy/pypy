from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef
from pypy.rpython.rctypes.tool import ctypes_platform
from pypy.rpython.rctypes.tool.libc import libc
import sys, math
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

def sieve(space, n):
    lst = range(2, n + 1)
    head = 0
    while 1:
        first = lst[head]
        if first > math.sqrt(n) + 1:
            lst_w = [space.newint(i) for i in lst]
            return space.newlist(lst_w)
        newlst = []
        for element in lst:
            if element <= first:
                newlst.append(element)
            elif element % first != 0:
                newlst.append(element)
        lst = newlst
        head += 1
sieve.unwrap_spec = [ObjSpace, int]
 
class W_MyType(Wrappable):
    def __init__(self, space, x=1):
        self.space = space
        self.x = x

    def multiply(self, w_y):
        space = self.space
        y = space.int_w(w_y)
        return space.wrap(self.x * y)

    def fget_x(space, self):
        return space.wrap(self.x)

    def fset_x(space, self, w_value):
        self.x = space.int_w(w_value)

def mytype_new(space, w_subtype, x):
    return space.wrap(W_MyType(space, x))
mytype_new.unwrap_spec = [ObjSpace, W_Root, int]

W_MyType.typedef = TypeDef('MyType',
    __new__ = interp2app(mytype_new)
)
