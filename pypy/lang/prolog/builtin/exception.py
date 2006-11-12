import py
from pypy.lang.prolog.interpreter import engine as enginemod, helper, term, error
from pypy.lang.prolog.builtin.register import expose_builtin
from pypy.lang.prolog.builtin.type import impl_ground

# ___________________________________________________________________
# exception handling

def impl_catch(engine, goal, catcher, recover, continuation):
    catching_continuation = enginemod.LimitedScopeContinuation(continuation)
    old_state = engine.frame.branch()
    try:
        return engine.call(goal, catching_continuation)
    except error.CatchableError, e:
        if not catching_continuation.scope_active:
            raise
        exc_term = e.term.getvalue(engine.frame)
        engine.frame.revert(old_state)
        d = {}
        exc_term = exc_term.clone_compress_vars(d, engine.frame.maxvar())
        engine.frame.extend(len(d))
        try:
            impl_ground(engine, exc_term)
        except error.UnificationFailed:
            raise error.UncatchableError(
                "not implemented: catching of non-ground terms")
        try:
            catcher.unify(exc_term, engine.frame)
        except error.UnificationFailed:
            if isinstance(e, error.UserError):
                raise error.UserError(exc_term)
            if isinstance(e, error.CatchableError):
                raise error.CatchableError(exc_term)
        return engine.call(recover, continuation)
expose_builtin(impl_catch, "catch", unwrap_spec=["callable", "obj", "callable"],
               handles_continuation=True)

def impl_throw(engine, exc):
    try:
        impl_ground(engine, exc)
    except error.UnificationFailed:
        raise error.UncatchableError(
            "not implemented: raising of non-ground terms")
    raise error.UserError(exc)
expose_builtin(impl_throw, "throw", unwrap_spec=["obj"])


