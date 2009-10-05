from pypy.jit.metainterp.policy import JitPolicy

class PyPyJitPolicy(JitPolicy):

    def __init__(self, translator=None):
        pass       # xxx

    def look_inside_function(self, func):
        mod = func.__module__ or '?'
        if (func.__name__.startswith('_mm_') or
            func.__name__.startswith('__mm_')):
            # multimethods
            return True
        if '_mth_mm_' in func.__name__:    # e.g. str_mth_mm_join_xxx
            return True
        
        # weakref support
        if mod == 'pypy.objspace.std.typeobject':
            if func.__name__ in ['get_subclasses', 'add_subclass',
                                 'remove_subclass']:
                return False

        if mod.startswith('pypy.objspace.'):
            # gc_id operation
            if func.__name__ == 'id__ANY':
                return False
        if mod == 'pypy.rlib.rbigint':
            #if func.__name__ == '_bigint_true_divide':
            return False
        if mod == 'pypy.rpython.lltypesystem.module.ll_math':
            # XXX temporary, contains force_cast
            return False
        if '_geninterp_' in func.func_globals: # skip all geninterped stuff
            return False
        if mod.startswith('pypy.interpreter.astcompiler.'):
            return False
        if mod.startswith('pypy.interpreter.pyparser.'):
            return False
        if mod.startswith('pypy.module.'):
            if mod.startswith('pypy.module.__builtin__'):
                if mod.endswith('operation') or mod.endswith('abstractinst'):
                    return True

            modname = mod.split('.')[2]
            if modname in ['pypyjit', 'signal', 'micronumpy', 'math']:
                return True
            return False
            
        if mod.startswith('pypy.translator.'):
            return False
        # string builder interface
        if mod == 'pypy.rpython.lltypesystem.rbuilder':
            return False
        # rweakvaluedict implementation
        if mod == 'pypy.rlib.rweakrefimpl':
            return False
        #if (mod == 'pypy.rpython.rlist' or
        #    mod == 'pypy.rpython.lltypesystem.rdict' or
        #    mod == 'pypy.rpython.lltypesystem.rlist'):
        #    # non oopspeced list or dict operations are helpers
        #    return False
        #if func.__name__ == 'll_update':
        #    return False
        
        return super(PyPyJitPolicy, self).look_inside_function(func)
