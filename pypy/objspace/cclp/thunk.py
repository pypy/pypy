from pypy.module._stackless.coroutine import _AppThunk
from pypy.module._stackless.interp_coroutine import AbstractThunk

from pypy.objspace.cclp.misc import w
from pypy.objspace.cclp.global_state import scheduler
from pypy.objspace.cclp.types import W_Var, W_Future, W_FailedValue, ConsistencyError, Solution
from pypy.objspace.cclp.interp_var import interp_wait, interp_entail, interp_bind, interp_free


def logic_args(args):
    "returns logic vars found in unpacked normalized args"
    assert isinstance(args, tuple)
    pos = args[0]
    kwa = args[1]
    pos_l = [arg for arg in pos
             if isinstance(arg, W_Var)]
    kwa_l = [arg for arg in kwa.keys()
             if isinstance(arg, W_Var)]
    return pos_l + kwa_l

#-- Thunk -----------------------------------------


class ProcedureThunk(_AppThunk):
    def __init__(self, space, w_callable, args, coro):
        _AppThunk.__init__(self, space, coro.costate, w_callable, args)
        self._coro = coro

    def call(self):
        w(".! initial (returnless) thunk CALL in", str(id(self._coro)))
        scheduler[0].trace_vars(self._coro, logic_args(self.args.unpack()))
        try:
            try:
                _AppThunk.call(self)
            except Exception, exc:
                w(".! exceptional EXIT of procedure", str(id(self._coro)), "with", str(exc))
                scheduler[0].dirty_traced_vars(self._coro, W_FailedValue(exc))
                self._coro._dead = True
            else:
                w(".! clean EXIT of procedure", str(id(self._coro)))
        finally:
            scheduler[0].remove_thread(self._coro)
            scheduler[0].schedule()


class FutureThunk(_AppThunk):
    def __init__(self, space, w_callable, args, w_Result, coro):
        _AppThunk.__init__(self, space, coro.costate, w_callable, args)
        self.w_Result = w_Result 
        self._coro = coro

    def call(self):
        w(".! initial thunk CALL in", str(id(self._coro)))
        scheduler[0].trace_vars(self._coro, logic_args(self.args.unpack()))
        try:
            try:
                _AppThunk.call(self)
            except Exception, exc:
                w(".! exceptional EXIT of future", str(id(self._coro)), "with", str(exc))
                failed_val = W_FailedValue(exc)
                self.space.bind(self.w_Result, failed_val)
                scheduler[0].dirty_traced_vars(self._coro, failed_val)
                self._coro._dead = True
            else:
                w(".! clean EXIT of future", str(id(self._coro)),
                  "-- setting future result", str(self.w_Result), "to",
                  str(self.costate.w_tempval))
                self.space.unify(self.w_Result, self.costate.w_tempval)
        finally:
            scheduler[0].remove_thread(self._coro)
            scheduler[0].schedule()

class CSpaceThunk(_AppThunk):
    def __init__(self, space, w_callable, args, coro):
        _AppThunk.__init__(self, space, coro.costate, w_callable, args)
        self._coro = coro

    def call(self):
        w("-- initial thunk CALL in", str(id(self._coro)))
        scheduler[0].trace_vars(self._coro, logic_args(self.args.unpack()))
        cspace = self._coro._cspace
        try:
            try:
                _AppThunk.call(self)
            except Exception, exc:
                w("-- exceptional EXIT of cspace", str(id(self._coro)), "with", str(exc))
                import traceback
                traceback.print_exc()
                scheduler[0].dirty_traced_vars(self._coro, W_FailedValue(exc))
                self._coro._dead = True
                self.space.bind(cspace._choice, self.space.wrap(SPACE_FAILURE))
            else:
                w("-- clean (valueless) EXIT of cspace", str(id(self._coro)))
                self.space.bind(cspace._solution, self.costate.w_tempval)
        finally:
            scheduler[0].remove_thread(self._coro)
            scheduler[0].schedule()


class PropagatorThunk(AbstractThunk):
    def __init__(self, space, w_constraint, coro):
        self.space = space
        self.coro = coro
        self.const = w_constraint

    def call(self):
        try:
            cspace = self.coro._cspace
            try:
                while 1:
                    entailed = self.const.revise()
                    if entailed:
                        break
                    Obs = W_Var(self.space)
                    interp_entail(cspace._finished, Obs)
                    for Sync in [var.w_dom.give_synchronizer()
                                 for var in self.const._variables]:
                        interp_entail(Sync, Obs)
                    interp_wait(self.space, Obs)
                    if not interp_free(cspace._finished):
                        break
            except ConsistencyError:
                cspace.fail()
            except:
                import traceback
                traceback.print_exc()
        finally:
            self.coro._dead = True
            scheduler[0].remove_thread(self.coro)
            scheduler[0].schedule()


class DistributorThunk(AbstractThunk):
    def __init__(self, space, w_distributor, coro):
        self.space = space
        self.coro = coro
        self.dist = w_distributor

    def call(self):
        coro = self.coro
        try:
            cspace = coro._cspace
            dist = self.dist
            try:
                while dist.distributable():
                    choice = cspace.choose(dist.fanout())
                    dist.distribute(choice)
                w("-- DISTRIBUTOR thunk exited because a solution was found")
                for var in cspace._solution.w_bound_to.wrappeditems:
                    assert var.w_dom.size() == 1
                    interp_bind(var, var.w_dom.get_values()[0])
                assert interp_free(cspace._choice)
                interp_bind(cspace._choice, self.space.newint(1))
            except ConsistencyError, e:
                w("-- DISTRIBUTOR thunk exited because", str(e))
                interp_bind(cspace._choice, self.space.newint(0))
                import traceback
                traceback.print_exc()
            except:
                import traceback
                traceback.print_exc()
        finally:
            interp_bind(cspace._finished, True)
            coro._dead = True
            scheduler[0].remove_thread(coro)
            scheduler[0].schedule()
        
