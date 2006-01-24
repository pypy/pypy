"""
The rctypes implementaion is contained here.
"""

from ctypes import *
from ctypes import _FUNCFLAG_CDECL, _FUNCFLAG_STDCALL
from pypy.annotation.model import SomeInteger
from pypy.rpython.lltypesystem.lltype import Signed


c_int.annotator_type = SomeInteger()
c_int.ll_type = Signed


class FunctionPointerTranslation(object):

        def compute_result_annotation(self, *args_s):
            """
            Answer the annotation of the external function's result
            """
            return self.restype.annotator_type

        def __hash__(self):
            return id(self)

        def specialize(self, hop):
            return hop.llops.gencapicall(self.__name__, hop.args_v,
                         resulttype=self.restype.ll_type, _callable=None,
                         convert_params=self.convert_params) 

        def convert_params(self, backend, param_info_list):
            raise NotImplementedError


class RCDLL(CDLL):
    """
    This is the restricted version of ctypes' CDLL class.
    """

    class _CdeclFuncPtr(FunctionPointerTranslation, CDLL._CdeclFuncPtr):
        """
        A simple extension of ctypes function pointers that
        implements a simple interface to the anotator.
        """
        _flags_ = _FUNCFLAG_CDECL



class RWinDLL(WinDLL):
    """
    This is the restricted version of ctypes' WINDLL class
    """

    class _StdcallFuncPtr(FunctionPointerTranslation, WinDLL._StdcallFuncPtr):
        """
        A simple extension of ctypes function pointers that
        implements a simple interface to the anotator.
        """
        _flags_ = _FUNCFLAG_STDCALL

