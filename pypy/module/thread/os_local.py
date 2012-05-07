from pypy.rlib.rweakref import RWeakKeyDictionary
from pypy.interpreter.baseobjspace import Wrappable, W_Root
from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.typedef import (TypeDef, interp2app, GetSetProperty,
    descr_get_dict)


class Local(Wrappable):
    """Thread-local data"""

    def __init__(self, space, initargs):
        self.initargs = initargs
        self.dicts = RWeakKeyDictionary(ExecutionContext, W_Root)
        # The app-level __init__() will be called by the general
        # instance-creation logic.  It causes getdict() to be
        # immediately called.  If we don't prepare and set a w_dict
        # for the current thread, then this would in cause getdict()
        # to call __init__() a second time.
        ec = space.getexecutioncontext()
        w_dict = space.newdict(instance=True)
        self.dicts.set(ec, w_dict)

    def getdict(self, space):
        ec = space.getexecutioncontext()
        w_dict = self.dicts.get(ec)
        if w_dict is None:
            # create a new dict for this thread
            w_dict = space.newdict(instance=True)
            self.dicts.set(ec, w_dict)
            # call __init__
            try:
                w_self = space.wrap(self)
                w_type = space.type(w_self)
                w_init = space.getattr(w_type, space.wrap("__init__"))
                space.call_obj_args(w_init, w_self, self.initargs)
            except:
                # failed, forget w_dict and propagate the exception
                self.dicts.set(ec, None)
                raise
            # ready
        return w_dict

    def descr_local__new__(space, w_subtype, __args__):
        local = space.allocate_instance(Local, w_subtype)
        Local.__init__(local, space, __args__)
        return space.wrap(local)

    def descr_local__init__(self, space):
        # No arguments allowed
        pass

Local.typedef = TypeDef("thread._local",
                        __doc__ = "Thread-local data",
                        __new__ = interp2app(Local.descr_local__new__.im_func),
                        __init__ = interp2app(Local.descr_local__init__),
                        __dict__ = GetSetProperty(descr_get_dict, cls=Local),
                        )
