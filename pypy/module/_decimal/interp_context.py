from rpython.rlib import rmpdec
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import (TypeDef, interp_attrproperty_w)
from pypy.interpreter.executioncontext import ExecutionContext


# The SignalDict is a MutableMapping that provides access to the
# mpd_context_t flags, which reside in the context object.
# When a new context is created, context.traps and context.flags are
# initialized to new SignalDicts.
# Once a SignalDict is tied to a context, it cannot be deleted.
class W_SignalDictMixin(W_Root):
    pass

def descr_new_signaldict(space, w_subtype):
    w_result = space.allocate_instance(W_SignalDictMixin, w_subtype)
    W_SignalDictMixin.__init__(w_result)
    return w_result

W_SignalDictMixin.typedef = TypeDef(
    'SignalDictMixin',
    __new__ = interp2app(descr_new_signaldict),
    )


class State:
    def __init__(self, space):
        w_import = space.builtin.get('__import__')
        w_collections = space.call_function(w_import,
                                            space.wrap('collections'))
        w_MutableMapping = space.getattr(w_collections,
                                         space.wrap('MutableMapping'))
        self.W_SignalDict = space.call_function(
            space.w_type, space.wrap("SignalDict"),
            space.newtuple([space.gettypeobject(W_SignalDictMixin.typedef),
                            w_MutableMapping]),
            space.newdict())

def state_get(space):
    return space.fromcache(State)


class W_Context(W_Root):
    def __init__(self, space):
        self.w_flags = space.call_function(state_get(space).W_SignalDict)

    def copy_w(self, space):
        w_copy = W_Context(space)
        # XXX incomplete
        return w_copy

def descr_new_context(space, w_subtype, __args__):
    w_result = space.allocate_instance(W_Context, w_subtype)
    W_Context.__init__(w_result, space)
    return w_result

W_Context.typedef = TypeDef(
    'Context',
    copy=interp2app(W_Context.copy_w),
    flags=interp_attrproperty_w('w_flags', W_Context),
    __new__ = interp2app(descr_new_context),
    )


ExecutionContext.decimal_context = None

def getcontext(space):
    ec = space.getexecutioncontext()
    if not ec.decimal_context:
        # Set up a new thread local context
        ec.decimal_context = W_Context(space)
    return ec.decimal_context

def setcontext(space, w_context):
    ec = space.getexecutioncontext()
    ec.decimal_context = w_context
