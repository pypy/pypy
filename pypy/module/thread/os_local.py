from pypy.module.thread import ll_thread as thread
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef, interp2app
from pypy.interpreter.typedef import GetSetProperty, descr_get_dict
from pypy.interpreter.typedef import descr_set_dict


class Local(Wrappable):
    """Thread-local data"""

    def __init__(self, space, initargs):
        self.initargs = initargs
        ident = thread.get_ident()
        self.dicts = {ident: space.newdict(instance=True)}

    def getdict(self, space):
        ident = thread.get_ident()
        try:
            w_dict = self.dicts[ident]
        except KeyError:
            # create a new dict for this thread
            w_dict = self.dicts[ident] = space.newdict(instance=True)
            # call __init__
            try:
                w_self = space.wrap(self)
                w_type = space.type(w_self)
                w_init = space.getattr(w_type, space.wrap("__init__"))
                space.call_obj_args(w_init, w_self, self.initargs)
            except:
                # failed, forget w_dict and propagate the exception
                del self.dicts[ident]
                raise
            # ready
            space.threadlocals.atthreadexit(space, finish_thread, self)
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

def finish_thread(w_obj):
    assert isinstance(w_obj, Local)
    ident = thread.get_ident()
    del w_obj.dicts[ident]
