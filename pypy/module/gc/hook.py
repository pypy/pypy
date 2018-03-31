from rpython.memory.gc.hook import GcHooks
from rpython.rlib.nonconst import NonConstant
from rpython.rlib.rarithmetic import r_uint
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, interp_attrproperty
from pypy.interpreter.executioncontext import AsyncAction

class LowLevelGcHooks(GcHooks):

    def setspace(self, space):
        self.space = space
        self.hooks = space.fromcache(AppLevelHooks)

    def is_gc_minor_enabled(self):
        return self.hooks.gc_minor_enabled

    def on_gc_minor(self, total_memory_used, pinned_objects):
        action = self.hooks.gc_minor
        action.total_memory_used = total_memory_used
        action.pinned_objects = pinned_objects
        action.fire()

    def on_gc_collect_step(self, oldstate, newstate):
        pass

    def on_gc_collect(self, count, arenas_count_before, arenas_count_after,
                      arenas_bytes, rawmalloc_bytes_before,
                      rawmalloc_bytes_after):
        pass


gchooks = LowLevelGcHooks()

class AppLevelHooks(object):

    def __init__(self, space):
        self.space = space
        self.gc_minor_enabled = False
        self.gc_minor = GcMinorHookAction(space)

    def set_hooks(self, space, w_on_gc_minor):
        self.gc_minor_enabled = not space.is_none(w_on_gc_minor)
        self.gc_minor.w_callable = w_on_gc_minor
        self.gc_minor.fix_annotation()


class GcMinorHookAction(AsyncAction):
    w_callable = None
    total_memory_used = 0
    pinned_objects = 0

    def fix_annotation(self):
        # the annotation of the class and its attributes must be completed
        # BEFORE we do the gc transform; this makes sure that everything is
        # annotated with the correct types
        if NonConstant(False):
            self.total_memory_used = NonConstant(r_uint(42))
            self.pinned_objects = NonConstant(-42)
            self.fire()

    def perform(self, ec, frame):
        w_stats = W_GcMinorStats(self.total_memory_used, self.pinned_objects)
        self.space.call_function(self.w_callable, w_stats)


class W_GcMinorStats(W_Root):

    def __init__(self, total_memory_used, pinned_objects):
        self.total_memory_used = total_memory_used
        self.pinned_objects = pinned_objects


W_GcMinorStats.typedef = TypeDef(
    "GcMinorStats",
    total_memory_used = interp_attrproperty("total_memory_used",
                                            cls=W_GcMinorStats, wrapfn="newint"),
    pinned_objects = interp_attrproperty("pinned_objects",
                                         cls=W_GcMinorStats, wrapfn="newint"),
    )


def set_hooks(space, w_on_gc_minor):
    space.fromcache(AppLevelHooks).set_hooks(space, w_on_gc_minor)
