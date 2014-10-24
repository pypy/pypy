
from rpython.rlib import jit_hooks
from rpython.rlib.jit import JitHookInterface, Counters

from pypy.interpreter.error import OperationError
from pypy.module.pypyjit.interp_resop import (Cache, wrap_greenkey,
    WrappedOp, W_JitLoopInfo, wrap_oplist)

class PyPyJitIface(JitHookInterface):
    def on_abort(self, reason, jitdriver, greenkey, greenkey_repr, logops, operations):
        space = self.space
        cache = space.fromcache(Cache)
        if cache.in_recursion:
            return
        if space.is_true(cache.w_abort_hook):
            cache.in_recursion = True
            oplist_w = wrap_oplist(space, logops, operations)
            try:
                try:
                    space.call_function(cache.w_abort_hook,
                        space.wrap(jitdriver.name),
                        wrap_greenkey(space, jitdriver, greenkey, greenkey_repr),
                        space.wrap(Counters.counter_names[reason]),
                        space.newlist(oplist_w)
                    )
                except OperationError, e:
                    e.write_unraisable(space, "jit hook ", cache.w_abort_hook)
            finally:
                cache.in_recursion = False

    def after_compile(self, debug_info):
        self._compile_hook(debug_info, is_bridge=False)

    def after_compile_bridge(self, debug_info):
        self._compile_hook(debug_info, is_bridge=True)

    def before_compile(self, debug_info):
        self._optimize_hook(debug_info, is_bridge=False)

    def before_compile_bridge(self, debug_info):
        self._optimize_hook(debug_info, is_bridge=True)

    def _compile_hook(self, debug_info, is_bridge):
        space = self.space
        cache = space.fromcache(Cache)
        if cache.in_recursion:
            return
        if space.is_true(cache.w_compile_hook):
            w_debug_info = W_JitLoopInfo(space, debug_info, is_bridge)
            cache.in_recursion = True
            try:
                try:
                    space.call_function(cache.w_compile_hook,
                                        space.wrap(w_debug_info))
                except OperationError, e:
                    e.write_unraisable(space, "jit hook ", cache.w_compile_hook)
            finally:
                cache.in_recursion = False

    def _optimize_hook(self, debug_info, is_bridge=False):
        space = self.space
        cache = space.fromcache(Cache)
        if cache.in_recursion:
            return
        if space.is_true(cache.w_optimize_hook):
            w_debug_info = W_JitLoopInfo(space, debug_info, is_bridge)
            cache.in_recursion = True
            try:
                try:
                    w_res = space.call_function(cache.w_optimize_hook,
                                                space.wrap(w_debug_info))
                    if space.is_w(w_res, space.w_None):
                        return
                    l = []
                    for w_item in space.listview(w_res):
                        item = space.interp_w(WrappedOp, w_item)
                        l.append(jit_hooks._cast_to_resop(item.op))
                    del debug_info.operations[:] # modifying operations above is
                    # probably not a great idea since types may not work
                    # and we'll end up with half-working list and
                    # a segfault/fatal RPython error
                    for elem in l:
                        debug_info.operations.append(elem)
                except OperationError, e:
                    e.write_unraisable(space, "jit hook ", cache.w_compile_hook)
            finally:
                cache.in_recursion = False

pypy_hooks = PyPyJitIface()
