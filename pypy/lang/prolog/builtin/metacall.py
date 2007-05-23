import py
from pypy.lang.prolog.interpreter import engine, helper, term, error
from pypy.lang.prolog.builtin.register import expose_builtin

# ___________________________________________________________________
# meta-call predicates

def impl_call(engine, call, continuation):
    try:
        return engine.call(call, continuation)
    except error.CutException, e:
        return e.continuation.call(engine, choice_point=False)
expose_builtin(impl_call, "call", unwrap_spec=["callable"],
               handles_continuation=True)

def impl_once(engine, clause, continuation):
    engine.call(clause)
    return continuation.call(engine, choice_point=False)
expose_builtin(impl_once, "once", unwrap_spec=["callable"],
               handles_continuation=True)

