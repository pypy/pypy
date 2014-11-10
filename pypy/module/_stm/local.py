"""
The '_stm.local' class, used for 'thread._local' with STM.
"""

from pypy.interpreter.gateway import W_Root, interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty, descr_get_dict
from rpython.rlib import jit
from rpython.rlib.objectmodel import we_are_translated


def _fill_untranslated(ec):
    if not we_are_translated() and not hasattr(ec, '_thread_local_dicts'):
        from pypy.module._stm.ec import initialize_execution_context
        initialize_execution_context(ec)


class STMLocal(W_Root):
    """Thread-local data"""

    @jit.dont_look_inside
    def __init__(self, space, initargs):
        self.space = space
        self.initargs = initargs
        # The app-level __init__() will be called by the general
        # instance-creation logic.  It causes getdict() to be
        # immediately called.  If we don't prepare and set a w_dict
        # for the current thread, then this would in cause getdict()
        # to call __init__() a second time.
        ec = space.getexecutioncontext()
        _fill_untranslated(ec)
        w_dict = space.newdict(instance=True)
        ec._thread_local_dicts.set(self, w_dict)

    @jit.dont_look_inside
    def create_new_dict(self, ec):
        # create a new dict for this thread
        space = self.space
        w_dict = space.newdict(instance=True)
        ec._thread_local_dicts.set(self, w_dict)
        # call __init__
        try:
            w_self = space.wrap(self)
            w_type = space.type(w_self)
            w_init = space.getattr(w_type, space.wrap("__init__"))
            space.call_obj_args(w_init, w_self, self.initargs)
        except:
            # failed, forget w_dict and propagate the exception
            ec._thread_local_dicts.set(self, None)
            raise
        # ready
        return w_dict

    def getdict(self, space):
        ec = space.getexecutioncontext()
        _fill_untranslated(ec)
        w_dict = ec._thread_local_dicts.get(self)
        if w_dict is None:
            w_dict = self.create_new_dict(ec)
        return w_dict

    def descr_local__new__(space, w_subtype, __args__):
        local = space.allocate_instance(STMLocal, w_subtype)
        STMLocal.__init__(local, space, __args__)
        return space.wrap(local)

    def descr_local__init__(self, space):
        # No arguments allowed
        pass

STMLocal.typedef = TypeDef("_stm.local",
                     __doc__ = "Thread-local data",
                     __new__ = interp2app(STMLocal.descr_local__new__.im_func),
                     __init__ = interp2app(STMLocal.descr_local__init__),
                     __dict__ = GetSetProperty(descr_get_dict, cls=STMLocal),
                     )
