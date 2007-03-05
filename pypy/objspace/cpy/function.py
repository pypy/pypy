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

    def __init__(self, original_sig):
        self.orig_arg = iter(original_sig.argnames).next
        self.inputargs = []
        self.wrappings = []
        self.passedargs = []
        self.miniglobals = {}
        self.star_arg = False

    def visit__ObjSpace(self, el):
        argname = self.orig_arg()
        assert argname == 'space'
        self.passedargs.append('___space')

    def visit__W_Root(self, el):
        argname = self.orig_arg()
        assert argname.startswith('w_')
        basename = argname[2:]
        self.inputargs.append(basename)
        self.wrappings.append('%s = ___W_Object(%s)' % (argname, basename))
        self.passedargs.append(argname)

    def visit__Wrappable(self, el):
        clsname = el.__name__     # XXX name clashes, but in gateway.py too
        self.miniglobals[clsname] = el
        argname = self.orig_arg()
        assert not argname.startswith('w_')
        self.inputargs.append(argname)
        self.wrappings.append('%s = ___space.interp_w(%s, ___W_Object(%s))'
                               % (argname,
                                  clsname,
                                  argname))
        self.passedargs.append(argname)

    def visit__object(self, el):
        convertermap = {int: 'int_w',
                        str: 'str_w',
                        float: 'float_w',
                        "index": 'getindex_w'
                        }
        argname = self.orig_arg()
        assert not argname.startswith('w_')
        self.inputargs.append(argname)
        self.wrappings.append('%s = ___space.%s(___W_Object(%s))' %
                               (argname,
                                convertermap[el],
                                argname))
        self.passedargs.append(argname)

    def visit_index(self, el):
        self.visit__object("index")

    def visit_args_w(self, el):
        argname = self.orig_arg()
        assert argname.endswith('_w')
        basename = argname[:-2]
        self.inputargs.append('*' + basename)
        self.wrappings.append('%s = []' % (argname,))
        self.wrappings.append('for ___i in range(len(%s)):' % (basename,))
        self.wrappings.append('    %s.append(___W_Object(%s[___i]))' % (
            argname, basename))
        self.passedargs.append(argname)
        self.star_arg = True

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
        bltin = func.code._bltin
        unwrap_spec = func.code._unwrap_spec
        from pypy.interpreter import pycode
        argnames, varargname, kwargname = pycode.cpython_code_signature(
            bltin.func_code)
        orig_sig = Signature(bltin, argnames, varargname, kwargname)

        tramp = UnwrapSpec_Trampoline(orig_sig)
        tramp.miniglobals = {
            '___space':           space,
            '___W_Object':        CPyObjSpace.W_Object,
            '___bltin':           bltin,
            '___OperationError':  OperationError,
            '___reraise':         reraise,
            }
        tramp.apply_over(unwrap_spec)

        sourcelines = ['def trampoline(%s):' % (', '.join(tramp.inputargs),)]
        # this description is to aid viewing in graphviewer
        sourcelines.append('    "wrapper for fn: %s"' % func.name)
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
        trampoline.star_arg = tramp.star_arg
        trampoline.allow_someobjects = True    # annotator hint
        trampoline._annspecialcase_ = "specialize:all_someobjects"
        if func.defs_w:
            trampoline.func_defaults = tuple([space.unwrap(w_x)
                                              for w_x in func.defs_w])
        w_result = W_Object(trampoline)
        space.wrap_cache[id(w_result)] = w_result, func, follow_annotations
        return w_result


def follow_annotations(bookkeeper, w_trampoline):
    from pypy.annotation import model as annmodel
    trampoline = w_trampoline.value
    s_trampoline = bookkeeper.immutablevalue(trampoline)
    args_s = [annmodel.SomeObject()] * trampoline.nb_args
    if trampoline.star_arg:
        args_s[-1] = Ellipsis   # hack, see bookkeeper.RPythonCallsSpace
    uniquekey = trampoline
    bookkeeper.emulate_pbc_call(uniquekey, s_trampoline, args_s)
