"""
Support to turn Function objects into W_Objects containing a built-in
function of CPython.
"""

import py
from pypy.objspace.cpy.capi import *
from pypy.objspace.cpy.refcount import Py_XIncref
from pypy.objspace.cpy.objspace import CPyObjSpace
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import BuiltinCode, ObjSpace, W_Root
from pypy.interpreter.gateway import UnwrapSpecRecipe, Signature
from pypy.interpreter.baseobjspace import SpaceCache
from pypy.tool.sourcetools import func_with_new_name


class UnwrapSpec_Trampoline(UnwrapSpecRecipe):

    def visit__ObjSpace(self, el, orig_sig, tramp):
        argname = orig_sig.next_arg()
        assert argname == 'space'
        tramp.passedargs.append('___space')

    def visit__W_Root(self, el, orig_sig, tramp):
        argname = orig_sig.next_arg()
        assert argname.startswith('w_')
        basename = argname[2:]
        tramp.inputargs.append(basename)
        tramp.wrappings.append('%s = ___W_Object(%s)' % (argname, basename))
        tramp.passedargs.append(argname)

    def visit__Wrappable(self, el, orig_sig, tramp):
        clsname = el.__name__     # XXX name clashes, but in gateway.py too
        tramp.miniglobals[clsname] = el
        argname = orig_sig.next_arg()
        assert not argname.startswith('w_')
        tramp.inputargs.append(argname)
        tramp.wrappings.append('%s = ___space.interp_w(%s, ___W_Object(%s))'
                               % (argname,
                                  clsname,
                                  argname))
        tramp.passedargs.append(argname)

    def visit__object(self, el, orig_sig, tramp):
        convertermap = {int: 'int_w',
                        str: 'str_w',
                        float: 'float_w'}
        argname = orig_sig.next_arg()
        assert not argname.startswith('w_')
        tramp.inputargs.append(argname)
        tramp.wrappings.append('%s = ___space.%s(___W_Object(%s))' %
                               (argname,
                                convertermap[el],
                                argname))
        tramp.passedargs.append(argname)

    def visit_args_w(self, el, orig_sig, tramp):
        argname = orig_sig.next_arg()
        assert argname.endswith('_w')
        basename = argname[:-2]
        tramp.inputargs.append('*' + basename)
        tramp.wrappings.append('%s = []' % (argname,))
        tramp.wrappings.append('for ___i in range(len(%s)):' % (basename,))
        tramp.wrappings.append('    %s.append(___W_Object(%s[___i]))' % (
            argname, basename))
        tramp.passedargs.append(argname)


class TrampolineSignature(object):

    def __init__(self):
        self.inputargs = []
        self.wrappings = []
        self.passedargs = []
        self.miniglobals = {}


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


class FunctionCache(SpaceCache):
    def build(cache, func):
        space = cache.space
        # make a built-in function
        assert isinstance(func.code, BuiltinCode)   # XXX
        factory = func.code.framefactory
        bltin = factory.behavior
        unwrap_spec = factory.unwrap_spec

        tramp = TrampolineSignature()
        tramp.miniglobals = {
            '___space':           space,
            '___W_Object':        CPyObjSpace.W_Object,
            '___bltin':           bltin,
            '___OperationError':  OperationError,
            '___reraise':         reraise,
            }

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
        sourcelines.append('    try:')
        sourcelines.append('        w_result = ___bltin(%s)' % (
            ', '.join(tramp.passedargs),))
        sourcelines.append('    except ___OperationError, e:')
        sourcelines.append('        ___reraise(e)')
        # the following line is not reached, unless we are translated
        # in which case it makes the function return (PyObject*)NULL.
        sourcelines.append('        w_result = ___W_Object()')
        sourcelines.append('    else:')
        #                           # convert None to Py_None
        sourcelines.append('        if w_result is None:')
        sourcelines.append('            return None')
        sourcelines.append('    return w_result.value')
        sourcelines.append('')

        miniglobals = tramp.miniglobals
        exec py.code.Source('\n'.join(sourcelines)).compile() in miniglobals

        trampoline = miniglobals['trampoline']
        trampoline = func_with_new_name(trampoline, func.name)
        trampoline.nb_args = len(tramp.inputargs)
        trampoline.allow_someobjects = True    # annotator hint
        w_result = W_Object(trampoline)
        space.wrap_cache[id(w_result)] = w_result, func, follow_annotations
        return w_result


def follow_annotations(bookkeeper, w_trampoline):
    from pypy.annotation import model as annmodel
    trampoline = w_trampoline.value
    s_trampoline = bookkeeper.immutablevalue(trampoline)
    args_s = [annmodel.SomeObject()] * trampoline.nb_args
    uniquekey = trampoline
    bookkeeper.emulate_pbc_call(uniquekey, s_trampoline, args_s)
