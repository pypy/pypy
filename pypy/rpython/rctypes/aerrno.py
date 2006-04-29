"""
Helpers to access the C-level 'errno' variable.
"""
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.annotation import model as annmodel
from ctypes import pythonapi, py_object


##def setfromerrno(exc=OSError):
##    """Raise an exception of the given class with the last failed C library
##    function's errno."""
##    pythonapi.PyErr_SetFromErrno(py_object(exc))

def geterrno():
    """Return the current 'errno' value."""
    try:
        pythonapi.PyErr_SetFromErrno(py_object(OSError))
    except OSError, e:
        return e.errno
    else:
        raise RuntimeError("setfromerrno() should have raised")


class GetErrnoFnEntry(ExtRegistryEntry):
    "Annotation and rtyping of calls to geterrno()"
    _about_ = geterrno

    def compute_result_annotation(self):
        return annmodel.SomeInteger()

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        return hop.llops.gencapicall('geterrno', [],
                                     resulttype = lltype.Signed,
                                     includes = (),
                                     _callable = geterrno)
