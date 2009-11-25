from pypy.module.thread import ll_thread as thread
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef, interp2app
from pypy.interpreter.typedef import GetSetProperty, descr_get_dict
from pypy.interpreter.typedef import descr_set_dict
from pypy.interpreter.gateway import ObjSpace, W_Root, Arguments


class Local(Wrappable):
    """Thread-local data"""

    def __init__(self, space, initargs):
        self.space = space
        self.initargs = initargs
        ident = thread.get_ident()
        self.dicts = {ident: space.newdict()}

    def getdict(self):
        ident = thread.get_ident()
        try:
            w_dict = self.dicts[ident]
        except KeyError:
            # create a new dict for this thread
            space = self.space
            w_dict = self.dicts[ident] = space.newdict()
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

    def setdict(self, space, w_dict):
        if not space.is_true(space.isinstance(w_dict, space.w_dict)):
            raise OperationError(space.w_TypeError,
                                space.wrap("setting dictionary to a non-dict"))
        self.getdict()   # force a dict to exist first
        ident = thread.get_ident()
        self.dicts[ident] = w_dict

    def descr_local__new__(space, w_subtype, __args__):
        # XXX check __args__
        local = space.allocate_instance(Local, w_subtype)
        Local.__init__(local, space, __args__)
        return space.wrap(local)

Local.typedef = TypeDef("thread._local",
                        __doc__ = "Thread-local data",
                        __new__ = interp2app(Local.descr_local__new__.im_func,
                                    unwrap_spec=[ObjSpace, W_Root, Arguments]),
                        __dict__ = GetSetProperty(descr_get_dict,
                                                  descr_set_dict, cls=Local),
                        )

def getlocaltype(space):
    return space.gettypeobject(Local.typedef)


def finish_thread(w_obj):
    assert isinstance(w_obj, Local)
    ident = thread.get_ident()
    del w_obj.dicts[ident]
