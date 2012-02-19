from pypy.translator.stm.gcsource import GcSource
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation


RETURNS_LOCAL_POINTER = set([
    'malloc', 'malloc_varsize', 'malloc_nonmovable',
    'malloc_nonmovable_varsize',
    'stm_writebarrier',
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
        try:
            srcs = self.gsrc[variable]
        except KeyError:
            # XXX we shouldn't get here, but we do translating the whole
            # pypy.  We should investigate at some point.  In the meantime
            # returning False is always safe.
            self.reason = 'variable not in gsrc!'
            return False
        for src in srcs:
            if isinstance(src, SpaceOperation):
                if src.opname in RETURNS_LOCAL_POINTER:
                    continue
                if src.opname == 'hint' and 'stm_write' in src.args[1].value:
                    continue
                self.reason = src
                return False
            elif isinstance(src, Constant):
                if src.value:     # a NULL pointer is still valid as local
                    self.reason = src
                    return False
            elif src == 'instantiate':
                pass
            elif src == 'originally_a_callee':
                pass
            elif isinstance(src, str):
                self.reason = src
                return False
            else:
                raise AssertionError(repr(src))
        return True

    def assert_local(self, variable, graph='?'):
        if self.is_local(variable):
            return   # fine
        else:
            raise AssertionError(
                "assert_local() failed (%s, %s):\n%r" % (variable, graph,
                                                         self.reason))
