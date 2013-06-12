import py
from prolog.interpreter import continuation, helper, term, error
from prolog.builtin.register import expose_builtin
from prolog.builtin.type import impl_ground

# ___________________________________________________________________
# exception handling

@expose_builtin("catch", unwrap_spec=["callable", "obj", "callable"],
                handles_continuation=True, needs_module=True)
def impl_catch(engine, heap, module, goal, catcher, recover, scont, fcont):
    scont = continuation.CatchingDelimiter(engine, module, scont, fcont, catcher, recover, heap)
    scont = continuation.CutScopeNotifier(engine, scont, fcont)
    scont = continuation.BodyContinuation(engine, module, scont, goal)
    #continuation.view(scont, fcont, heap)
    return scont, fcont, heap.branch()

@expose_builtin("throw", unwrap_spec=["obj"], handles_continuation=True)
def impl_throw(engine, heap, exc, scont, fcont):
    return engine.throw(exc, scont, fcont, heap)

