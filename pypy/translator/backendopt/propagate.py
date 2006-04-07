from pypy.objspace.flow.model import Block, Variable, Constant, c_last_exception
from pypy.objspace.flow.model import traverse, mkentrymap, checkgraph
from pypy.objspace.flow.model import SpaceOperation
from pypy.rpython.lltypesystem import lltype, lloperation
from pypy.rpython.llinterp import LLInterpreter, LLFrame
from pypy.translator import simplify
from pypy.translator.simplify import get_graph
from pypy.translator.backendopt.removenoops import remove_same_as
from pypy.translator.backendopt.inline import OP_WEIGHTS

def do_atmost(n, f, *args):
    i = 0
    while f(*args):
        i += 1
        if i > n:
            break
    return i > 0

def rewire_links(graph):
    """This function changes the target of certain links: this happens
    if the exitswitch is passed along the link to another block where
    it is again used as the exitswitch. This situation occurs after the
    inlining of functions that return a bool."""
    entrymap = mkentrymap(graph)
    candidates = {}
    for block in graph.iterblocks():
        if (isinstance(block.exitswitch, Variable) and
            block.exitswitch.concretetype is lltype.Bool):
            for val, link in enumerate(block.exits):
                val = bool(val)
                try:
                    index = link.args.index(block.exitswitch)
                except ValueError:
                    continue
                if len(link.target.operations) > 0:
                    continue
                var = link.target.inputargs[index]
                if link.target.exitswitch is var:
                    candidates[block] = val
    for block, val in candidates.iteritems():
        link = block.exits[val]
        args = []
        for arg in link.target.exits[val].args:
            if isinstance(arg, Constant):
                args.append(arg)
            else:
                index = link.target.inputargs.index(arg)
                args.append(link.args[index])
        link.target = link.target.exits[val].target
        link.args = args
    if candidates:
        print "rewiring links in graph", graph.name
        simplify.join_blocks(graph)
        return True
    return False

def coalesce_links(graph):
    done = False
    for block in graph.iterblocks():
        if len(block.exits) != 2:
            continue
        if block.exitswitch == c_last_exception:
            continue
        if not (block.exits[0].args == block.exits[1].args and
            block.exits[0].target is block.exits[1].target):
            continue
        done = True
        block.exitswitch = None
        block.exits = block.exits[:1]
        block.exits[0].exitcase = None
    if done:
        return True
    else:
        return False

def propagate_consts(graph):
    """replace a variable of the inputargs of a block by a constant
    if all blocks leading to it have the same constant in that position"""
    entrymap = mkentrymap(graph)
    candidates = []
    changed = False
    for block, ingoing in entrymap.iteritems():
        if block in [graph.returnblock, graph.exceptblock]:
            continue
        for i in range(len(ingoing[0].args) - 1, -1, -1):
            vals = {}
            withvar = True
            for link in ingoing:
                if isinstance(link.args[i], Variable):
                    break
                else:
                    vals[link.args[i]] = True
            else:
               withvar = False
            if len(vals) != 1 or withvar:
                continue
            print "propagating constants in graph", graph.name
            const = vals.keys()[0]
            for link in ingoing:
                del link.args[i]
            var = block.inputargs[i]
            del block.inputargs[i]
            op = SpaceOperation("same_as", [const], var)
            block.operations.insert(0, op)
            changed = True
    if changed:
        remove_same_as(graph)
        checkgraph(graph)
        return True
    return False

class TooManyOperations(Exception):
    pass

class CountingLLFrame(LLFrame):
    def __init__(self, graph, args, llinterpreter, f_back=None, maxcount=1000):
        super(CountingLLFrame, self).__init__(graph, args, llinterpreter, f_back)
        self.count = 0
        self.maxcount = maxcount

    def eval_operation(self, operation):
        if operation is None: #can happen in the middle of constant folding
            return
        self.count += OP_WEIGHTS.get(operation.opname, 1)
        if self.count > self.maxcount:
            raise TooManyOperations
        return super(CountingLLFrame, self).eval_operation(operation)

def constant_folding(graph, translator):
    """do constant folding if the arguments of an operations are constants"""
    lli = LLInterpreter(translator.rtyper)
    llframe = LLFrame(graph, None, lli)
    changed = False
    for block in graph.iterblocks():
        for i, op in enumerate(block.operations):
            if sum([isinstance(arg, Variable) for arg in op.args]):
                continue
            if lloperation.LL_OPERATIONS[op.opname].canfold:
                print "folding operation", op, "in graph", graph.name
                try:
                    llframe.eval_operation(op)
                except:
                    print "did not work"
                else:
                    res = Constant(llframe.getval(op.result))
                    print "result", res.value
                    res.concretetype = op.result.concretetype
                    block.operations[i].opname = "same_as"
                    block.operations[i].args = [res]
                    changed = True
            # disabling the code for now, since it is not correct
            elif 0: #op.opname == "direct_call":
                called_graph = get_graph(op.args[0], translator)
                if (called_graph is not None and
                    simplify.has_no_side_effects(translator, called_graph) and
                    (block.exitswitch != c_last_exception or 
                     i != len(block.operations) - 1)):
                    args = [arg.value for arg in op.args[1:]]
                    countingframe = CountingLLFrame(called_graph, args, lli)
                    print "folding call", op, "in graph", graph.name
                    try:
                        res = countingframe.eval()
                    except:
                        print "did not work"
                        pass
                    else:
                        print "result", res
                        res = Constant(res)
                        res.concretetype = op.result.concretetype
                        block.operations[i].opname = "same_as"
                        block.operations[i].args = [res]
                        changed = True
        block.operations = [op for op in block.operations if op is not None]
    if changed:
        remove_same_as(graph)
        propagate_consts(graph)
        checkgraph(graph)
        return True
    return False

def partial_folding_once(graph, translator):
    lli = LLInterpreter(translator.rtyper)
    entrymap = mkentrymap(graph)
    def visit(block):
        if (not isinstance(block, Block) or block is graph.startblock or
            block is graph.returnblock or block is graph.exceptblock):
            return
        usedvars = {}
        for op in block.operations:
            if not lloperation.LL_OPERATIONS[op.opname].canfold:
                return
            for arg in op.args:
                if (isinstance(arg, Variable) and arg in block.inputargs):
                    usedvars[arg] = True
        if isinstance(block.exitswitch, Variable):
            usedvars[block.exitswitch] = True
        pattern = [arg in usedvars for arg in block.inputargs]
        for link in entrymap[block]:
            s = sum([isinstance(arg, Constant) or not p
                         for arg, p in zip(link.args, pattern)])
            if s != len(link.args):
                continue
            args = []
            for i, arg in enumerate(link.args):
                if isinstance(arg, Constant):
                    args.append(arg.value)
                else:
                    assert not pattern[i]
                    args.append(arg.concretetype._example())
            llframe = LLFrame(graph, None, lli)
            llframe.fillvars(block, args)
            nextblock, forwardargs = llframe.eval_block(block)
            if nextblock is not None:
                newargs = []
                for i, arg in enumerate(nextblock.inputargs):
                    try:
                        index = [l.target for l in block.exits].index(nextblock)
                        index = block.inputargs.index(block.exits[index].args[i])
                    except ValueError:
                        c = Constant(forwardargs[i])
                        c.concretetype = arg.concretetype
                        newargs.append(c)
                    else:
                        newargs.append(link.args[index])
            else:
                assert 0, "this should not occur"
            unchanged = link.target == nextblock and link.args == newargs
            link.target = nextblock
            link.args = newargs
            checkgraph(graph)
            if not unchanged:
                raise ValueError
    try:
        traverse(visit, graph)
    except ValueError:
        return True
    else:
        return False

def partial_folding(graph, translator):
    """this function does constant folding in the following situation:
    a block has a link that leads to it that has only constant args. Then all
    the operations of this block are evaluated and the link leading to the
    block is adjusted according to the resulting value of the exitswitch"""
    if do_atmost(1000, partial_folding_once, graph, translator):
        propagate_consts(graph)
        simplify.join_blocks(graph)
        return True
    else:
        return False


def propagate_all(translator):
    for graph in translator.graphs:
        def prop():
            changed = False
            changed = rewire_links(graph) or changed
            changed = propagate_consts(graph) or changed
            changed = coalesce_links(graph) or changed
            changed = do_atmost(100, constant_folding, graph,
                                           translator) or changed
            changed = partial_folding(graph, translator) or changed
            return changed
        do_atmost(10, prop)
