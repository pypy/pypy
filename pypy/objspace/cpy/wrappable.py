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
from pypy.interpreter.gateway import UnwrapSpecRecipe, Signature
from pypy.rpython import extregistry


class UnwrapSpec_Trampoline(UnwrapSpecRecipe):

    def visit__ObjSpace(self, el, orig_sig, tramp):
        argname = orig_sig.next_arg()
        assert argname == 'space'
        tramp.passedargs.append('___space')

    def visit__W_Root(self, el, orig_sig, tramp):
        argname = orig_sig.next_arg()
        assert argname.startswith('w_')
        basename = 'o_' + argname[2:]
        tramp.inputargs.append(basename)
        tramp.wrappings.append('%s = ___W_Object(%s)' % (argname, basename))
        tramp.passedargs.append(argname)

    def visit__object(self, el, orig_sig, tramp):
        convertermap = {int: '___PyInt_AsLong',
                        str: 'XXX',
                        float: 'XXX'}
        argname = orig_sig.next_arg()
        assert not argname.startswith('w_')
        basename = 'o_' + argname
        tramp.inputargs.append(basename)
        tramp.wrappings.append('%s = %s(%s)' % (argname,
                                                convertermap[el],
                                                basename))
        tramp.passedargs.append(argname)


class TrampolineSignature(object):

    def __init__(self):
        self.inputargs = []
        self.wrappings = []
        self.passedargs = []


class __extend__(pairtype(CPyObjSpace, BuiltinFunction)):

    def wrap((space, func)):
        # make a built-in function
        assert isinstance(func.code, BuiltinCode)
        factory = func.code.framefactory
        bltin = factory.behavior
        unwrap_spec = factory.unwrap_spec

        tramp = TrampolineSignature()

        from pypy.interpreter import pycode
        argnames, varargname, kwargname = pycode.cpython_code_signature(
            bltin.func_code)
        orig_sig = Signature(bltin, argnames, varargname, kwargname)

        orig_sig.apply_unwrap_spec(unwrap_spec,
                                   UnwrapSpec_Trampoline().dispatch,
                                   tramp)

        sourcelines = ['def trampoline(%s):' % (', '.join(tramp.inputargs),)]
        for line in tramp.wrappings:
            sourcelines.append('    ' + line)
        sourcelines.append('    w_result = ___bltin(%s)' % (
            ', '.join(tramp.passedargs),))
        sourcelines.append('    return w_result.value')
        sourcelines.append('')

        miniglobals = {
            '___space':        space,
            '___W_Object':     CPyObjSpace.W_Object,
            '___PyInt_AsLong': PyInt_AsLong,
            '___bltin':        bltin,
            }
        exec py.code.Source('\n'.join(sourcelines)).compile() in miniglobals

        trampoline = miniglobals['trampoline']
        trampoline.allow_someobjects = True    # annotator hint
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
