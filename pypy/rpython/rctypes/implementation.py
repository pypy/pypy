"""
The rctypes implementaion is contained here.
"""

import sys
from ctypes import *
from ctypes import _FUNCFLAG_CDECL
if sys.platform == "win32":
    from ctypes import _FUNCFLAG_STDCALL
from pypy.annotation.model import SomeInteger, SomeCTypesObject
from pypy.rpython.lltypesystem.lltype import Signed

c_int.annotator_type = SomeInteger()
c_int.ll_type = Signed
c_char_p.annotator_type = None
c_char_p.ll_type = None
c_char_p.wrap_arg = staticmethod(
        lambda ll_type, arg_name: "RPyString_AsString(%s)" % arg_name)
POINTER(c_char).annotator_type = None
POINTER(c_char).ll_type = None
POINTER(c_char).wrap_arg = staticmethod(
        lambda ll_type, arg_name: "RPyString_AsString(%s)" % arg_name)


class FunctionPointerTranslation(object):

        def compute_result_annotation(self, *args_s):
            """
            Answer the annotation of the external function's result
            """
            try:
                return self.restype.annotator_type
            except AttributeError:
                return SomeCTypesObject(self.restype)

        def __hash__(self):
            return id(self)

        def specialize(self, hop):
            return hop.llops.gencapicall(self.__name__, hop.args_v,
                         resulttype=self.restype.ll_type, _callable=None,
                         convert_params=self.convert_params) 

        def convert_params(self, backend, param_info_list):
            assert "c" == backend.lower()
            assert self.argtypes is not None
            answer = []
            for ctype_type, (ll_type, arg_name) in zip(self.argtypes, param_info_list):
                if ll_type == ctype_type.ll_type:
                    answer.append(arg_name)
                else:
                    answer.append(ctype_type.wrap_arg(ll_type, arg_name))
            return answer


class RStructureMeta(type(Structure)):
    def __new__(mta,name,bases,clsdict):
        _fields = clsdict.get('_fields_',None)
        _adict = {}
        if _fields is not None:
            for attr, atype in _fields:
                _adict[attr] = atype
        clsdict['_fields_def_'] = _adict

        return super(RStructureMeta,mta).__new__(mta, name, bases, clsdict)

class RStructure(Structure):

    __metaclass__ = RStructureMeta

    def compute_annotation(cls):
        return SomeCTypesObject(cls)
    compute_annotation = classmethod(compute_annotation)

    def compute_result_annotation(cls, *args_s):
        """
        Answer the result annotation of calling 'cls'.
        """
        return SomeCTypesObject(cls)
    compute_result_annotation = classmethod(compute_result_annotation)

class RByrefObj(object):

    def __init__(self):
        self.__name__ = 'RByrefObj'

    def compute_result_annotation(cls, s_arg):
        """
        Answer the result annotation of calling 'byref'.
        """
        return SomeCTypesObject(POINTER(s_arg.knowntype))

    compute_result_annotation = classmethod(compute_result_annotation)

    def __call__(self,obj):
        return byref(obj)

RByref = RByrefObj()


def RPOINTER(cls):
    answer = POINTER(cls)
    def compute_result_annotation(cls, s_arg):
        """
        Answer the result annotation of calling 'cls'.
        """
        assert answer is cls
        return SomeCTypesObject(cls)
    answer.compute_result_annotation = classmethod(compute_result_annotation)
    return answer


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



if sys.platform == "win32":
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

