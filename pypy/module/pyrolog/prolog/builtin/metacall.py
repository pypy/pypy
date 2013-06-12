import py
from prolog.interpreter import continuation, helper, term, error
from prolog.builtin.register import expose_builtin

# ___________________________________________________________________
# meta-call predicates

@expose_builtin("call", unwrap_spec=["callable"],
                handles_continuation=True, needs_module=True)
def impl_call(engine, heap, module, call, scont, fcont):
    scont = continuation.CutScopeNotifier.insert_scope_notifier(engine, scont, fcont)
    return engine.call(call, module, scont, fcont, heap)

class OnceContinuation(continuation.Continuation):
    def __init__(self, engine, nextcont, fcont):
        continuation.Continuation.__init__(self, engine, nextcont)
        self.fcont = fcont

    def activate(self, fcont, heap):
        return self.nextcont, self.fcont, heap

@expose_builtin("once", unwrap_spec=["callable"],
                handles_continuation=True, needs_module=True)
def impl_once(engine, heap, module, clause, scont, fcont):
    scont = OnceContinuation(engine, scont, fcont)
    return engine.call(clause, module, scont, fcont, heap)

