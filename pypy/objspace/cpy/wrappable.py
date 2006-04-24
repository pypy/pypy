"""
Support to turn interpreter objects (subclasses of Wrappable)
into CPython objects (subclasses of W_Object).
"""

import py
from pypy.annotation.pairtype import pair, pairtype
from pypy.objspace.cpy.capi import *
from pypy.objspace.cpy.objspace import CPyObjSpace
from pypy.interpreter.function import BuiltinFunction
from pypy.interpreter.gateway import BuiltinCode, ObjSpace, W_Root


class __extend__(pairtype(CPyObjSpace, BuiltinFunction)):

    def wrap((space, func)):
        # make a built-in function
        assert isinstance(func.code, BuiltinCode)
        factory = func.code.framefactory
        bltin = factory.behavior
        unwrap_spec = factory.unwrap_spec

        assert unwrap_spec == [ObjSpace, W_Root]    # XXX for now

        # make a real CPython built-in function from a PyMethodDef
        def callback(w_self, w_args):
            "XXX minimalistic"
            w_a = PyObject_GetItem(w_args, 0)
            w_result = bltin(space, w_a)
            return w_result

        ml = PyMethodDef(ml_name  = factory.b_name,
                         ml_meth  = PyCFunction(callback),
                         ml_flags = METH_VARARGS,
                         #ml_doc  = ...,
                         )
        w_result = PyCFunction_NewEx(byref(ml), None, func.w_module)
        w_result.ml = ml   # keep ml alive as long as w_result is around
        return w_result
