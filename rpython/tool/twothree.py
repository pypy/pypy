"""
Helpers for python2, python3 compatiblity
"""

import sys

def metaclass(meta):
    def metaclass_wrapper(cls):
        __name = str(cls.__name__)
        __bases = tuple(cls.__bases__)
        __dict = dict(cls.__dict__)

        for each_slot in __dict.get("__slots__", tuple()):
            __dict.pop(each_slot, None)

        __dict["__metaclass__"] = meta

        __dict["__wrapped__"] = cls

        return(meta(__name, __bases, __dict))
    return(metaclass_wrapper)

if sys.version_info[0] == 2:
    exec("def reraise(tp, value, tb=None):\n    raise tp, value, tb\n")
else:    
    def reraise(tp, value, tb=None):
        if value is None:
            value = tp()
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

