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

        assert unwrap_spec[0] == ObjSpace
        for spec in unwrap_spec[1:]:
            assert spec == W_Root      # XXX

        def trampoline(*args):
            args_w = [space.wrap(a) for a in args]
            w_result = bltin(space, *args_w)
            return space.unwrap(w_result)

        w_result = W_Object(trampoline)

        # override the annotation behavior of 'w_result'
        # to emulate a call to the bltin function at interp-level
        BaseEntry = extregistry._lookup_cls(w_result)
        uniquekey = bltin
        nb_args = len(unwrap_spec) - 1

        class TrampolineEntry(BaseEntry):
            _about_ = w_result
            def compute_annotation(self):
                from pypy.annotation.bookkeeper import getbookkeeper
                bookkeeper = getbookkeeper()
                s_bltin = bookkeeper.immutablevalue(bltin)
                s_space = bookkeeper.immutablevalue(space)
                s_w_obj = bookkeeper.valueoftype(W_Object)
                args_s = [s_space] + [s_w_obj]*nb_args
                s_result = bookkeeper.emulate_pbc_call(uniquekey, s_bltin,
                                                       args_s)
                assert s_w_obj.contains(s_result), (
                    "%r should return a wrapped obj, got %r instead" % (
                    bltin, s_result))
                return super(TrampolineEntry, self).compute_annotation()

        return w_result
