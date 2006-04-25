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
from pypy.rpython import extregistry


class __extend__(pairtype(CPyObjSpace, BuiltinFunction)):

    def wrap((space, func)):
        # make a built-in function
        assert isinstance(func.code, BuiltinCode)
        factory = func.code.framefactory
        bltin = factory.behavior
        unwrap_spec = factory.unwrap_spec

        assert unwrap_spec == [ObjSpace, W_Root]    # XXX for now

        def trampoline(a):
            w_arg = space.W_Object(a)
            w_result = bltin(space, w_arg)
            return w_result.value

        w_result = W_Object(trampoline)

        # override the annotation behavior of 'w_result'
        # to emulate a call to the trampoline() function at interp-level
        BaseEntry = extregistry._lookup_cls(w_result)
        uniquekey = trampoline
        nb_args = len(unwrap_spec) - 1

        class TrampolineEntry(BaseEntry):
            _about_ = w_result

            def compute_annotation(self):
                from pypy.annotation import model as annmodel
                from pypy.annotation.bookkeeper import getbookkeeper

                bookkeeper = getbookkeeper()
                if bookkeeper is not None:   # else probably already rtyping
                    s_trampoline = bookkeeper.immutablevalue(trampoline)
                    args_s = [annmodel.SomeObject()]*nb_args
                    bookkeeper.emulate_pbc_call(uniquekey, s_trampoline,
                                                args_s)
                return super(TrampolineEntry, self).compute_annotation()

        return w_result
