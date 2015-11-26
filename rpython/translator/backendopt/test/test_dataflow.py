import random
from rpython.tool.algo.unionfind import UnionFind
from rpython.translator.backendopt.dataflow import AbstractForwardDataFlowAnalysis



from rpython.translator.translator import TranslationContext, graphof


class SimpleForwardAnalysis(AbstractForwardDataFlowAnalysis):
    def __init__(self):
        self.seen = set()

    def transfer_function(self, block, in_state):
        self.seen.add(block)
        return in_state

    def entry_state(self, block):
        return True

    def initialize_block(self, block):
        return False, False

    def join_operation(self, preds_outs, inputargs, pred_out_args):
        return any(preds_outs)


def test_simple_forward_flow():
    def f(x):
        if x < 0:
            if x == -1:
                return x+1
            else:
                return x+2
        else:
            if x == 1:
                return x-1
            else:
                return x-2
    t = TranslationContext()
    g = t.buildflowgraph(f)
    sfa = SimpleForwardAnalysis()
    ins, outs = sfa.calculate(g)
    assert len(sfa.seen) == 8
    assert ins[g.startblock] == sfa.entry_state(None)
    assert outs[g.returnblock] == sfa.entry_state(None)

def test_loopy_forward_flow():
    def f(x):
        if x < 0:
            while x:
                pass
            return x
        else:
            while x:
                if x-1:
                    return x
    t = TranslationContext()
    g = t.buildflowgraph(f)
    sfa = SimpleForwardAnalysis()
    ins, outs = sfa.calculate(g)
    g.show()
    assert len(sfa.seen) == 5
    assert ins[g.startblock] == sfa.entry_state(None)
    assert outs[g.returnblock] == sfa.entry_state(None)
