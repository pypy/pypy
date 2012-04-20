from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import (TypeDef, interp2app, GetSetProperty,
    descr_get_dict)
from pypy.module.transaction.interp_transaction import state


class W_Local(Wrappable):
    """Thread-local data.  Behaves like a regular object, but its content
    is not shared between multiple concurrently-running transactions.
    It can be accessed without conflicts.

    It can be used for purely transaction-local data.

    It can also be used for long-living caches that store values that
    are (1) not too costly to compute and (2) not too memory-hungry,
    because they will end up being computed and stored once per actual
    thread.
    """

    def __init__(self, space):
        self.dicts = []
        self._update_dicts(space)
        # unless we call transaction.set_num_threads() afterwards, this
        # 'local' object is now initialized with the correct number of
        # dictionaries, to avoid conflicts later if _update_dicts() is
        # called in a transaction.

    def _update_dicts(self, space):
        new = state.get_number_of_threads() - len(self.dicts)
        if new <= 0:
            return
        # update the list without appending to it (to keep it non-resizable)
        self.dicts = self.dicts + [space.newdict(instance=True)
                                   for i in range(new)]

    def getdict(self, space):
        n = state.get_thread_number()
        try:
            return self.dicts[n]
        except IndexError:
            self._update_dicts(space)
            assert n < len(self.dicts)
            return self.dicts[n]

def descr_local__new__(space, w_subtype):
    local = W_Local(space)
    return space.wrap(local)

W_Local.typedef = TypeDef("transaction.local",
            __new__ = interp2app(descr_local__new__),
            __dict__ = GetSetProperty(descr_get_dict, cls=W_Local),
            )
W_Local.typedef.acceptable_as_base_class = False
