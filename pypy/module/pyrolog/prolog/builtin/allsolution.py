import py
from prolog.interpreter import helper, term, error, continuation, memo
from prolog.builtin.register import expose_builtin

# ___________________________________________________________________
# finding all solutions to a goal

class FindallContinuation(continuation.Continuation):
    def __init__(self, engine, template, heap, scont):
        # nextcont still needs to be set, for correct exception propagation
        continuation.Continuation.__init__(self, engine, scont)
        self.resultvar = self.fullsolution = heap.newvar()
        self.template = template
        self.heap = heap

    def activate(self, fcont, _):
        m = memo.CopyMemo()
        clone = self.template.copy(self.heap, m)
        newresultvar = self.heap.newvar()
        result = term.Callable.build(".", [clone, newresultvar])
        self.resultvar.setvalue(result, self.heap)
        self.resultvar = newresultvar
        raise error.UnificationFailed()

class DoneWithFindallContinuation(continuation.FailureContinuation):
    def __init__(self, engine, scont, fcont, heap, collector, bag):
        continuation.FailureContinuation.__init__(self, engine, scont, fcont, heap)
        self.collector = collector
        self.bag = bag

    def fail(self, heap):
        heap = heap.revert_upto(self.undoheap)
        result = term.Callable.build("[]")
        resultvar = self.collector.resultvar
        resultvar.setvalue(result, heap)
        self.bag.unify(self.collector.fullsolution, heap)
        return self.nextcont, self.orig_fcont, heap



@expose_builtin("findall", unwrap_spec=['raw', 'callable', 'raw'],
                handles_continuation=True, needs_module=True)
def impl_findall(engine, heap, module, template, goal, bag, scont, fcont):
    newheap = heap.branch()
    collector = FindallContinuation(engine, template, heap, scont)
    newscont = continuation.BodyContinuation(engine, module, collector, goal)
    fcont = DoneWithFindallContinuation(engine, scont, fcont, heap, collector, bag)
    return newscont, fcont, newheap
