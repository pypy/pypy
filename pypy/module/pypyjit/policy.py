import pypy
from pypy.jit.metainterp.policy import ManualJitPolicy

from pypy.translator.backendopt.support import find_calls_from

class PyPyJitPolicy(ManualJitPolicy):

    def look_inside_function(self, func):
        mod = func.__module__ or '?'
        if (func.__name__.startswith('_mm_') or
            func.__name__.startswith('__mm_')):
            # multimethods
            name = func.__name__.lstrip('_')
            if (name.startswith('mm_truediv') or
                name.startswith('mm_inplace_truediv') or
                name.startswith('mm_float')):
                # floats
                return False
            return True
        if '_mth_mm_' in func.__name__:    # e.g. str_mth_mm_join_xxx
            return True
        if mod.startswith('pypy.objspace.'):
            # we don't support floats
            if 'float' in mod or 'complex' in mod:
                return False
            if func.__name__ == 'format_float':
                return False
            # gc_id operation
            if func.__name__ == 'id__ANY':
                return False
            return True
        # floats
        if mod == 'pypy.rlib.rbigint':
            #if func.__name__ == '_bigint_true_divide':
            return False
        if '_geninterp_' in func.func_globals: # skip all geninterped stuff
            return False
        if mod.startswith('pypy.interpreter.astcompiler.'):
            return False
        if mod.startswith('pypy.interpreter.pyparser.'):
            return False
        if mod.startswith('pypy.module.'):
            if not mod.startswith('pypy.module.pypyjit.'):
                return False
        if mod.startswith('pypy.translator.'):
            return False
        # string builder interface
        if mod == 'pypy.rpython.lltypesystem.rbuilder':
            return False
        #if (mod == 'pypy.rpython.rlist' or
        #    mod == 'pypy.rpython.lltypesystem.rdict' or
        #    mod == 'pypy.rpython.lltypesystem.rlist'):
        #    # non oopspeced list or dict operations are helpers
        #    return False
        #if func.__name__ == 'll_update':
        #    return False

        # weakref support
        if (mod == 'pypy.objspace.std.typeobject' and
            func.__name__ == 'get_subclasses'):
            return False
        
        return super(PyPyJitPolicy, self).look_inside_function(func)
