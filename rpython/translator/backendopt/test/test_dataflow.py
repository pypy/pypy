import random
from rpython.tool.algo.unionfind import UnionFind
from rpython.translator.backendopt.dataflow import (
    AbstractForwardDataFlowAnalysis, postorder_block_list)

import pytest

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
        return False

    def join_operation(self, inputargs, preds_outs, links_to_preds):
        assert len(preds_outs) == len(links_to_preds)
        assert all((len(inputargs) == len(link.args) for link in links_to_preds))
        return any(preds_outs)

class NotSimpleForwardAnalysis(AbstractForwardDataFlowAnalysis):
    def __init__(self):
        self.seen = set()

    def transfer_function(self, block, in_state):
        self.seen.add(block)
        return in_state

    def entry_state(self, block):
        return False

    def initialize_block(self, block):
        return True

    def join_operation(self, inputargs, preds_outs, links_to_preds):
        assert len(preds_outs) == len(links_to_preds)
        assert all((len(inputargs) == len(link.args) for link in links_to_preds))
        return all(preds_outs)


@pytest.mark.parametrize("flow", [SimpleForwardAnalysis, NotSimpleForwardAnalysis])
def test_simple_forward_flow(flow):
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
    sfa = flow()
    ins, outs = sfa.calculate(g)
    assert len(sfa.seen) == 8
    assert ins[g.startblock] == sfa.entry_state(None)
    assert outs[g.returnblock] == sfa.entry_state(None)

@pytest.mark.parametrize("flow", [SimpleForwardAnalysis, NotSimpleForwardAnalysis])
def test_loopy_forward_flow(flow):
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
    sfa = flow()
    ins, outs = sfa.calculate(g)
    assert len(sfa.seen) == 5
    assert ins[g.startblock] == sfa.entry_state(None)
    assert outs[g.returnblock] == sfa.entry_state(None)


def test_postorder_block_list():
    def f(x):
        pass
    t = TranslationContext()
    g = t.buildflowgraph(f)
    pobl = postorder_block_list(g)
    assert len(set(pobl)) == 2 # start & return

    def f2(x):
        if x:
            x=x+1
        else:
            x=x+2
        return x
    t = TranslationContext()
    g = t.buildflowgraph(f2)
    pobl = postorder_block_list(g)
    assert len(pobl[0].exits) == 0
    assert len(pobl[1].exits) == 1
    assert len(pobl[2].exits) == 1
    assert len(pobl[3].exits) == 2
    assert len(set(pobl)) == 4


def test_postorder_block_list2():
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
    assert len(set(postorder_block_list(g))) == 5
