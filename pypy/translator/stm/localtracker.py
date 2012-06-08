from pypy.translator.stm.gcsource import GcSource
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation


RETURNS_LOCAL_POINTER = set([
    'malloc', 'malloc_varsize', 'malloc_nonmovable',
    'malloc_nonmovable_varsize',
    'stm_writebarrier',
    ])

ENSURED_LOCAL_VARS = False      # not needed for now


class StmLocalTracker(object):
    """Tracker to determine which pointers are statically known to point
    to local objects.  Here, 'local' versus 'global' is meant in the sense
    of the stmgc: a pointer is 'local' if it goes to the thread-local memory,
    and 'global' if it points to the shared read-only memory area."""

    def __init__(self, translator):
        self.translator = translator
        self.gsrc = GcSource(translator)
        # Set of variables on which we have called try_ensure_local()
        # and it returned True, or recursively the variables that
        # these variables depend on.  It is the set of variables
        # holding a value that we really want to be local.  It does
        # not contain the variables that happen to be local but whose
        # locality is not useful any more.
        if ENSURED_LOCAL_VARS:
            self.ensured_local_vars = set()

    def try_ensure_local(self, *variables):
        for variable in variables:
            if not self._could_be_local(variable):
                return False   # one of the passed-in variables cannot be local
        #
        # they could all be locals, so flag them and their dependencies
        # and return True
        if ENSURED_LOCAL_VARS:
            for variable in variables:
                if (isinstance(variable, Variable) and
                        variable not in self.ensured_local_vars):
                    depends_on = self.gsrc.backpropagate(variable)
                    self.ensured_local_vars.update(depends_on)
        return True

    def _could_be_local(self, variable):
        srcs = self.gsrc[variable]
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
            elif isinstance(src, str):
                self.reason = src
                return False
            else:
                raise AssertionError(repr(src))
        return True

    def assert_local(self, variable, graph='?'):
        if self.try_ensure_local(variable):
            return   # fine
        else:
            raise AssertionError(
                "assert_local() failed (%s, %s):\n%r" % (variable, graph,
                                                         self.reason))
