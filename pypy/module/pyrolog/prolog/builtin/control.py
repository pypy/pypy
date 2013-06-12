from prolog.interpreter import helper, term, error, continuation
from prolog.builtin.register import expose_builtin
from prolog.interpreter.signature import Signature

ifsig = Signature.getsignature("->", 2)
cutsig = Signature.getsignature("!", 0)
FAILATOM = term.Callable.build("fail")
TRUEATOM = term.Callable.build("true")

# ___________________________________________________________________
# control predicates

@expose_builtin("fail", unwrap_spec=[])
def impl_fail(engine, heap):
    raise error.UnificationFailed()

@expose_builtin("true", unwrap_spec=[])
def impl_true(engine, heap):
    return

@expose_builtin("repeat", unwrap_spec=[], handles_continuation=True)
def impl_repeat(engine, heap, scont, fcont):
    return scont, RepeatContinuation(engine, scont, fcont, heap), heap.branch()

class RepeatContinuation(continuation.FailureContinuation):
    def fail(self, heap):
        heap = heap.revert_upto(self.undoheap)
        return self.nextcont, self, heap

@expose_builtin("!", unwrap_spec=[], handles_continuation=True)
def impl_cut(engine, heap, scont, fcont):
    end_fcont = scont.find_end_of_cut()
    #import pdb; pdb.set_trace()
    fcont.cut(end_fcont, heap)
    return scont, end_fcont, heap

@expose_builtin(",", unwrap_spec=["callable", "raw"], 
        handles_continuation=True, needs_module=True)
def impl_and(engine, heap, module, call1, call2, scont, fcont):
    if not isinstance(call2, term.Var) and not isinstance(call2, term.Callable):
        return error.throw_type_error('callable', call2)
    scont = continuation.BodyContinuation(engine, module, scont, call2)
    return engine.call(call1, module, scont, fcont, heap)

class OrContinuation(continuation.FailureContinuation):
    def __init__(self, engine, module, nextcont, orig_fcont, undoheap, altcall):
        continuation.FailureContinuation.__init__(self, engine, nextcont, orig_fcont, undoheap)
        self.altcall = altcall
        assert undoheap is not None
        self.module = module

    def fail(self, heap):
        heap = heap.revert_upto(self.undoheap, discard_choicepoint=True)
        scont = continuation.BodyContinuation(self.engine, self.module, self.nextcont, self.altcall)
        return scont, self.orig_fcont, heap

    def __repr__(self):
        return "<OrContinuation %r" % (self.altcall, )


@expose_builtin(";", unwrap_spec=["callable", "callable"],
                handles_continuation=True, needs_module=True)
def impl_or(engine, heap, module, call1, call2, scont, fcont):
    # sucks a bit to have to special-case A -> B ; C here :-(
    if call1.signature().eq(ifsig):
        assert helper.is_term(call1)
        return if_then_else(
                engine, heap, module, scont, fcont,
                call1.argument_at(0),
                call1.argument_at(1), call2)
    else:
        fcont = OrContinuation(engine, module, scont, fcont, heap, call2)
        newscont = continuation.BodyContinuation(engine, module, scont, call1)
        return newscont, fcont, heap.branch()

def if_then_else(engine, heap, module, scont, fcont, if_clause, then_clause, else_clause):
    newfcont = OrContinuation(engine, module, scont, fcont, heap, else_clause)
    newscont, fcont, heap = impl_if(
            engine, heap, module, if_clause, then_clause, scont, newfcont, fcont)
    return newscont, fcont, heap.branch()

@expose_builtin("->", unwrap_spec=["callable", "raw"],
                handles_continuation=True, needs_module=True)
def impl_if(engine, heap, module, if_clause, then_clause, scont, fcont,
            fcont_after_condition=None):
    if fcont_after_condition is None:
        fcont_after_condition = fcont
    scont = continuation.BodyContinuation(engine, module, scont, then_clause)
    scont = IfScopeNotifier(engine, scont, fcont, fcont_after_condition)
    newscont = continuation.BodyContinuation(engine, module, scont, if_clause)
    return newscont, fcont, heap

class IfScopeNotifier(continuation.CutScopeNotifier):
    def __init__(self, engine, nextcont, fcont_after_cut, fcont_after_condition):
        continuation.CutScopeNotifier.__init__(self, engine, nextcont, fcont_after_cut)
        self.fcont_after_condition = fcont_after_condition

    def activate(self, fcont, heap):
        return self.nextcont, self.fcont_after_condition, heap

@expose_builtin(["not", "\\+"], unwrap_spec=["callable"],
                handles_continuation=True, needs_module=True)
def impl_not(engine, heap, module, call, scont, fcont):
    return if_then_else(engine, heap, module, scont, fcont, call, FAILATOM, TRUEATOM)
