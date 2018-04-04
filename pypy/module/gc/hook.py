from rpython.memory.gc.hook import GcHooks
from rpython.memory.gc import incminimark 
from rpython.rlib.nonconst import NonConstant
from rpython.rlib.rarithmetic import r_uint
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, interp_attrproperty
from pypy.interpreter.executioncontext import AsyncAction

class LowLevelGcHooks(GcHooks):

    def __init__(self, space):
        self.space = space
        self.hooks = space.fromcache(AppLevelHooks)

    def is_gc_minor_enabled(self):
        return self.hooks.gc_minor_enabled

    def is_gc_collect_step_enabled(self):
        return self.hooks.gc_collect_step_enabled

    def on_gc_minor(self, total_memory_used, pinned_objects):
        action = self.hooks.gc_minor
        action.total_memory_used = total_memory_used
        action.pinned_objects = pinned_objects
        action.fire()

    def on_gc_collect_step(self, oldstate, newstate):
        action = self.hooks.gc_collect_step
        action.oldstate = oldstate
        action.newstate = newstate
        action.fire()

    def on_gc_collect(self, count, arenas_count_before, arenas_count_after,
                      arenas_bytes, rawmalloc_bytes_before,
                      rawmalloc_bytes_after):
        pass


class AppLevelHooks(object):

    def __init__(self, space):
        self.space = space
        self.gc_minor_enabled = False
        self.gc_collect_step_enabled = False
        self.gc_minor = GcMinorHookAction(space)
        self.gc_collect_step = GcCollectStepHookAction(space)

    def set_hooks(self, space, w_on_gc_minor, w_on_gc_collect_step):
        self.gc_minor_enabled = not space.is_none(w_on_gc_minor)
        self.gc_minor.w_callable = w_on_gc_minor
        self.gc_minor.fix_annotation()
        #
        self.gc_collect_step_enabled = not space.is_none(w_on_gc_collect_step)
        self.gc_collect_step.w_callable = w_on_gc_collect_step
        self.gc_collect_step.fix_annotation()


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


class GcCollectStepHookAction(AsyncAction):
    w_callable = None
    oldstate = 0
    newstate = 0

    def fix_annotation(self):
        # the annotation of the class and its attributes must be completed
        # BEFORE we do the gc transform; this makes sure that everything is
        # annotated with the correct types
        if NonConstant(False):
            self.oldstate = NonConstant(42)
            self.newstate = NonConstant(-42)
            self.fire()

    def perform(self, ec, frame):
        w_stats = W_GcCollectStepStats(self.oldstate, self.newstate)
        self.space.call_function(self.w_callable, w_stats)


class W_GcMinorStats(W_Root):

    def __init__(self, total_memory_used, pinned_objects):
        self.total_memory_used = total_memory_used
        self.pinned_objects = pinned_objects


class W_GcCollectStepStats(W_Root):

    def __init__(self, oldstate, newstate):
        self.oldstate = oldstate
        self.newstate = newstate


W_GcMinorStats.typedef = TypeDef(
    "GcMinorStats",
    total_memory_used = interp_attrproperty("total_memory_used",
                                            cls=W_GcMinorStats, wrapfn="newint"),
    pinned_objects = interp_attrproperty("pinned_objects",
                                         cls=W_GcMinorStats, wrapfn="newint"),
    )

W_GcCollectStepStats.typedef = TypeDef(
    "GcCollectStepStats",
    STATE_SCANNING = incminimark.STATE_SCANNING,
    STATE_MARKING = incminimark.STATE_MARKING,
    STATE_SWEEPING = incminimark.STATE_SWEEPING,
    STATE_FINALIZING = incminimark.STATE_FINALIZING,
    GC_STATES = tuple(incminimark.GC_STATES),
    oldstate = interp_attrproperty("oldstate",
                                   cls=W_GcCollectStepStats, wrapfn="newint"),
    newstate = interp_attrproperty("newstate",
                                   cls=W_GcCollectStepStats, wrapfn="newint"),
    )


@unwrap_spec(w_on_gc_minor=WrappedDefault(None),
             w_on_gc_collect_step=WrappedDefault(None))
def set_hooks(space, w_on_gc_minor=None, w_on_gc_collect_step=None):
    hooks = space.fromcache(AppLevelHooks)
    hooks.set_hooks(space, w_on_gc_minor, w_on_gc_collect_step)
                                             
