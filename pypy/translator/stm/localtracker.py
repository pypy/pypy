from pypy.translator.stm.gcsource import GcSource
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation


RETURNS_LOCAL_POINTER = set([
    'malloc', 'malloc_varsize', 'malloc_nonmovable',
    'malloc_nonmovable_varsize',
    ])


class StmLocalTracker(object):
    """Tracker to determine which pointers are statically known to point
    to local objects.  Here, 'local' versus 'global' is meant in the sense
    of the stmgc: a pointer is 'local' if it goes to the thread-local memory,
    and 'global' if it points to the shared read-only memory area."""

    def __init__(self, translator):
        self.translator = translator
        self.gsrc = GcSource(translator)

    def is_local(self, variable):
        assert isinstance(variable, Variable)
        for src in self.gsrc[variable]:
            if isinstance(src, SpaceOperation):
                if src.opname not in RETURNS_LOCAL_POINTER:
                    return False
            elif isinstance(src, Constant):
                if src.value:     # a NULL pointer is still valid as local
                    return False
            elif src is None:
                return False
            else:
                raise AssertionError(src)
        return True
