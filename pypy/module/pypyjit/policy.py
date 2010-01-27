from pypy.jit.metainterp.policy import JitPolicy

class PyPyJitPolicy(JitPolicy):

    def look_inside_pypy_module(self, modname):
        if (modname == '__builtin__.operation' or
                modname == '__builtin__.abstractinst' or
                modname == '__builtin__.interp_classobj'):
            return True

        if '.' in modname:
            modname, _ = modname.split('.', 1)
        if modname in ['pypyjit', 'signal', 'micronumpy', 'math', 'exceptions']:
            return True
        return False

    def look_inside_function(self, func):
        # this function should never actually return True directly
        # but instead call the base implementation
        mod = func.__module__ or '?'
        
        if mod.startswith('pypy.objspace.'):
            # gc_id operation
            if func.__name__ == 'id__ANY':
                return False
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
            modname = mod[len('pypy.module.'):]
            if not self.look_inside_pypy_module(modname):
                return False
            
        return True
