"""
Support to turn interpreter objects (subclasses of Wrappable)
into CPython objects (subclasses of W_Object).
"""

from pypy.objspace.cpy.capi import *
from pypy.objspace.cpy.refcount import Py_XIncref

def reraise(e):
    w_type      = e.w_type
    w_value     = e.w_value
    w_traceback = e.application_traceback
    if e.application_traceback is None:
        w_traceback = W_Object()    # NULL
    else:
        Py_XIncref(w_traceback)
    Py_XIncref(w_type)
    Py_XIncref(w_value)
    RAW_PyErr_Restore(e.w_type, e.w_value, w_traceback)

