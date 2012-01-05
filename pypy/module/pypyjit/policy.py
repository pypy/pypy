from pypy.jit.codewriter.policy import JitPolicy
from pypy.rlib.jit import JitPortal
from pypy.module.pypyjit.interp_jit import Cache
from pypy.interpreter.error import OperationError
from pypy.jit.metainterp.jitprof import counter_names
from pypy.module.pypyjit.interp_resop import wrap_oplist
from pypy.interpreter.pycode import PyCode

class PyPyPortal(JitPortal):
    def on_abort(self, reason, jitdriver, greenkey):
        space = self.space
        cache = space.fromcache(Cache)
        if cache.in_recursion:
            return
        if space.is_true(cache.w_abort_hook):
            cache.in_recursion = True
            try:
                space.call_function(cache.w_abort_hook,
                                    space.wrap(counter_names[reason]))
            except OperationError, e:
                e.write_unraisable(space, "jit hook ", cache.w_abort_hook)
            cache.in_recursion = False

    def on_compile(self, jitdriver, logger, looptoken, operations, type,
                   greenkey, asmstart, asmlen):
        from pypy.rpython.annlowlevel import cast_base_ptr_to_instance

        space = self.space
        cache = space.fromcache(Cache)
        if cache.in_recursion:
            return
        if space.is_true(cache.w_compile_hook):
            logops = logger._make_log_operations()
            list_w = wrap_oplist(space, logops, operations)
            pycode = cast_base_ptr_to_instance(PyCode, ll_pycode)
            cache.in_recursion = True
            try:
                space.call_function(cache.w_compile_hook,
                                    space.wrap('main'),
                                    space.wrap(type),
                                    space.newtuple([pycode,
                                    space.wrap(next_instr),
                                    space.wrap(is_being_profiled)]),
                                    space.newlist(list_w))
            except OperationError, e:
                e.write_unraisable(space, "jit hook ", cache.w_compile_hook)
            cache.in_recursion = False

    def on_compile_bridge(self, jitdriver, logger, orig_looptoken, operations,
                          n, asm, asmlen):
        space = self.space
        cache = space.fromcache(Cache)
        if cache.in_recursion:
            return
        if space.is_true(cache.w_compile_hook):
            logops = logger._make_log_operations()
            list_w = wrap_oplist(space, logops, operations)
            cache.in_recursion = True
            try:
                space.call_function(cache.w_compile_hook,
                                    space.wrap('main'),
                                    space.wrap('bridge'),
                                    space.wrap(n),
                                    space.newlist(list_w))
            except OperationError, e:
                e.write_unraisable(space, "jit hook ", cache.w_compile_hook)
            cache.in_recursion = False

pypy_portal = PyPyPortal()

class PyPyJitPolicy(JitPolicy):

    def look_inside_pypy_module(self, modname):
        if (modname == '__builtin__.operation' or
                modname == '__builtin__.abstractinst' or
                modname == '__builtin__.interp_classobj' or
                modname == '__builtin__.functional' or
                modname == '__builtin__.descriptor' or
                modname == 'thread.os_local' or
                modname == 'thread.os_thread'):
            return True
        if '.' in modname:
            modname, _ = modname.split('.', 1)
        if modname in ['pypyjit', 'signal', 'micronumpy', 'math', 'exceptions',
                       'imp', 'sys', 'array', '_ffi', 'itertools', 'operator',
                       'posix', '_socket', '_sre', '_lsprof', '_weakref',
                       '__pypy__', 'cStringIO', '_collections', 'struct',
                       'mmap', 'marshal']:
            return True
        return False

    def look_inside_function(self, func):
        mod = func.__module__ or '?'

        if mod == 'pypy.rlib.rbigint' or mod == 'pypy.rlib.rlocale' or mod == 'pypy.rlib.rsocket':
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
