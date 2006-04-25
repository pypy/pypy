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


def builtin_function_builder(ml, w_module):
    """Build and initialize a real CPython built-in function object.
    Compiled into the extension module and called when it is
    first imported.
    """
    return PyCFunction_NewEx(byref(ml), None, w_module)


class __extend__(pairtype(CPyObjSpace, BuiltinFunction)):

    def wrap((space, func)):
        # make a built-in function
        assert isinstance(func.code, BuiltinCode)
        factory = func.code.framefactory
        bltin = factory.behavior
        unwrap_spec = factory.unwrap_spec

        assert unwrap_spec == [ObjSpace, W_Root]    # XXX for now

        # argh! callbacks of mode PyDLL are not supported by ctypes so far
        # (as of 0.9.9.4).  XXX hack.  I am not happy.

        # as a workaround, we use an interface that lets us return a normal
        # Python function used for testing, with an attached 'builder'
        # function that is executed at start-up to construct the object

        def trampoline(*args):
            # only called during testing; not compiled
            args_w = [space.W_Object(a) for a in args]
            w_result = bltin(space, *args_w)
            return w_result.value

        def callback(w_self, w_args):
            # only called when compiled into the extension module
            w_a = PyObject_GetItem(w_args, 0)
            w_result = bltin(space, w_a)
            return w_result

        ml = PyMethodDef(ml_name  = factory.b_name,
                         ml_meth  = PyCFunction(callback),
                         ml_flags = METH_VARARGS,
                         #ml_doc  = ...,
                         )

        w_result = W_Object(trampoline)
        w_result.builder = builtin_function_builder, (ml, func.w_module)
        return w_result
