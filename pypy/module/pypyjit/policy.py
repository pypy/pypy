from pypy.jit.codewriter.policy import JitPolicy
from pypy.rlib.jit import JitPortal
from pypy.interpreter.error import OperationError
from pypy.jit.metainterp.jitprof import counter_names
from pypy.module.pypyjit.interp_resop import wrap_oplist, Cache, wrap_greenkey

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
                                    space.wrap(jitdriver.name),
                                    wrap_greenkey(space, jitdriver, greenkey),
                                    space.wrap(counter_names[reason]))
            except OperationError, e:
                e.write_unraisable(space, "jit hook ", cache.w_abort_hook)
            cache.in_recursion = False

    def on_compile(self, jitdriver, logger, looptoken, operations, type,
                   greenkey, ops_offset, asmstart, asmlen):
        self._compile_hook(jitdriver, logger, operations, type,
                           ops_offset, asmstart, asmlen,
                           wrap_greenkey(self.space, jitdriver, greenkey))

    def on_compile_bridge(self, jitdriver, logger, orig_looptoken, operations,
                          n, ops_offset, asmstart, asmlen):
        self._compile_hook(jitdriver, logger, operations, 'bridge',
                           ops_offset, asmstart, asmlen,
                           self.space.wrap(n))

    def _compile_hook(self, jitdriver, logger, operations, type,
                      ops_offset, asmstart, asmlen, w_arg):
        space = self.space
        cache = space.fromcache(Cache)
        if cache.in_recursion:
            return
        if space.is_true(cache.w_compile_hook):
            logops = logger._make_log_operations()
            list_w = wrap_oplist(space, logops, operations, ops_offset)
            cache.in_recursion = True
            try:
                space.call_function(cache.w_compile_hook,
                                    space.wrap(jitdriver.name),
                                    space.wrap(type),
                                    w_arg,
                                    space.newlist(list_w),
                                    space.wrap(asmstart),
                                    space.wrap(asmlen))
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
            modname, rest = modname.split('.', 1)
        else:
            rest = ''
        if modname in ['pypyjit', 'signal', 'micronumpy', 'math', 'exceptions',
                       'imp', 'sys', 'array', '_ffi', 'itertools', 'operator',
                       'posix', '_socket', '_sre', '_lsprof', '_weakref',
                       '__pypy__', 'cStringIO', '_collections', 'struct',
                       'mmap', 'marshal']:
            if modname == 'pypyjit' and 'interp_resop' in rest:
                return False
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
