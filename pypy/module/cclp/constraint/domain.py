from pypy.module.cclp.types import W_Var
from pypy.module.cclp.interp_var import interp_bind, interp_free

from pypy.module._cslib import fd


class _DorkFiniteDomain(fd._FiniteDomain):
    """
    this variant accomodates synchronization needs
    of the dorkspace
    """

    def __init__(self, space, w_values, values):
        fd._FiniteDomain.__init__(self, w_values, values)
        self.space = space
        self._changevar = W_Var(space)

    def clear_change(self):
        "create a fresh change synchonizer"
        assert not interp_free(self._changevar)
        self._changevar = W_Var(self.space)

    def one_shot_watcher(self):
        return self._changevar
    
    def _value_removed(self):
        fd._FiniteDomain._value_removed(self)
        interp_bind(self._changevar, self.space.w_True)
        self.clear_change()


