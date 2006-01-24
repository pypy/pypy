"""
The rctypes implementaion is contained here.
"""

from ctypes import *
from ctypes import _FUNCFLAG_CDECL, _FUNCFLAG_STDCALL
from pypy.annotation.model import SomeInteger

c_int.annotator_type = SomeInteger()


class FunctionPointerAnnotation(object):

        def compute_result_annotation(self, *args_s):
            """
            Answer the annotation of the external function's result
            """
            return self.restype.annotator_type


class RCDLL(CDLL):
    """
    This is the restricted version of ctypes' CDLL class.
    """

    class _CdeclFuncPtr(FunctionPointerAnnotation, CDLL._CdeclFuncPtr):
        """
        A simple extension of ctypes function pointers that
        implements a simple interface to the anotator.
        """
        _flags_ = _FUNCFLAG_CDECL



class RWinDLL(WinDLL):
    """
    This is the restricted version of ctypes' WINDLL class
    """

    class _StdcallFuncPtr(FunctionPointerAnnotation, WinDLL._StdcallFuncPtr):
        """
        A simple extension of ctypes function pointers that
        implements a simple interface to the anotator.
        """
        _flags_ = _FUNCFLAG_STDCALL

