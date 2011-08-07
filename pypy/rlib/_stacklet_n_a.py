from pypy.rlib import _rffi_stacklet as _c
from pypy.rpython.annlowlevel import llhelper
from pypy.tool.staticmethods import StaticMethods


class StackletGcRootFinder:
    __metaclass__ = StaticMethods

    def new(thrd, callback, arg):
        h = _c.new(thrd, llhelper(_c.run_fn, callback), arg)
        if not h:
            raise MemoryError
        return h
    new._annspecialcase_ = 'specialize:arg(1)'

    def switch(thrd, h):
        h = _c.switch(thrd, h)
        if not h:
            raise MemoryError
        return h

    destroy = _c.destroy

    is_empty_handle = _c.is_empty_handle

    def get_null_handle():
        return _c.null_handle


gcrootfinder = StackletGcRootFinder    # class object
