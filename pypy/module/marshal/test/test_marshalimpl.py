from pypy.module.marshal import interp_marshal
from pypy.interpreter.error import OperationError
import sys

class TestInternalStuff:
    def test_nesting(self):
        space = self.space
        app_cost = interp_marshal.APPLEVEL_STACK_COST
        curdepth = space.getexecutioncontext().framestack.depth()
        for do_hack in (False, True):
            interp_marshal.DONT_USE_MM_HACK = not do_hack
            if not do_hack:
                interp_cost = 5
            else:
                interp_cost = 2
            stacklimit = interp_marshal.nesting_limit - (curdepth + 1) * app_cost - interp_marshal.TEST_CONST
            w_tup = space.newtuple([])
            tupdepth = 1
            for i in range(0, stacklimit - interp_cost-1, interp_cost):
                w_tup = space.newtuple([w_tup])
                tupdepth += 1
            w_good = w_tup
            s = interp_marshal.dumps(space, w_good, space.wrap(1))
            interp_marshal.loads(space, s)
            w_bad = space.newtuple([w_tup])
            raises(OperationError, interp_marshal.dumps, space, w_bad, space.wrap(1))
            print 'max sys depth = %d, mm_hack = %r, marshal limit = %d' % (
                sys.getrecursionlimit(), do_hack, tupdepth)

