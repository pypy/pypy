from pypy.objspace.flow.model import Block, Variable, Constant, c_last_exception
from pypy.objspace.flow.model import traverse, mkentrymap, checkgraph
from pypy.objspace.flow.model import SpaceOperation
from pypy.rpython.lltypesystem import lltype, lloperation
from pypy.rpython.llinterp import LLInterpreter, LLFrame
from pypy.translator import simplify
from pypy.translator.simplify import get_graph
from pypy.translator.backendopt.removenoops import remove_same_as
from pypy.translator.backendopt.inline import OP_WEIGHTS
from pypy.translator.backendopt.ssa import DataFlowFamilyBuilder
from pypy.translator.backendopt.support import log, var_needsgc

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
        #print "rewiring links in graph", graph.name
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
    if all blocks leading to it have the same constant in that position
    or if all non-constants that lead to it are in the same variable family
    as the constant that we go to."""
    entrymap = mkentrymap(graph)
    candidates = []
    changed = False
    variable_families = DataFlowFamilyBuilder(graph).get_variable_families()
    for block, ingoing in entrymap.iteritems():
        if block in [graph.returnblock, graph.exceptblock]:
            continue
        for i in range(len(ingoing[0].args) - 1, -1, -1):
            vals = {}
            var = block.inputargs[i]
            var_rep = variable_families.find_rep(var)
            withvar = True
            for link in ingoing:
                if isinstance(link.args[i], Variable):
                    if variable_families.find_rep(link.args[i]) != var_rep:
                        break
                else:
                    vals[link.args[i]] = True
            else:
                withvar = False
            if len(vals) != 1 or withvar:
                continue
            #print "propagating constants in graph", graph.name
            const = vals.keys()[0]
            for link in ingoing:
                del link.args[i]
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

def op_dont_fold(op):
    if op.opname in ('getfield', 'getarrayitem'):
        CONTAINER = op.args[0].concretetype.TO
        if CONTAINER._hints.get('immutable'):
            return False
    if op.opname in ("getsubstruct", "getarraysubstruct"):
        # this is needed so that the parent of the result (op.args[0])
        # does not go away after the op is folded. see test_dont_fold_getsubstruct
        if not var_needsgc(op.result):
            return True
        # XXX if the result is immortal, one could still fold...
    try:
        return not lloperation.LL_OPERATIONS[op.opname].canfold
    except KeyError:
        return True

def constant_folding(graph, translator):
    """do constant folding if the arguments of an operations are constants"""
    lli = LLInterpreter(translator.rtyper)
    llframe = LLFrame(graph, None, lli)
    changed = False
    for block in graph.iterblocks():
        for i, op in enumerate(block.operations):
            if sum([isinstance(arg, Variable) for arg in op.args]):
                continue
            if not op_dont_fold(op):
                try:
                    llframe.eval_operation(op)
                except:
                    pass
                else:
                    res = Constant(llframe.getval(op.result))
                    log.constantfolding("in graph %s, %s = %s" %
                                        (graph.name, op, res))
                    res.concretetype = op.result.concretetype
                    block.operations[i].opname = "same_as"
                    block.operations[i].args = [res]
                    changed = True
            elif op.opname == "direct_call":
                called_graph = get_graph(op.args[0], translator)
                if (called_graph is not None and
                    simplify.has_no_side_effects(
                        translator, called_graph,
                        is_operation_false=op_dont_fold) and
                    (block.exitswitch != c_last_exception or 
                     i != len(block.operations) - 1)):
                    args = [arg.value for arg in op.args[1:]]
                    countingframe = CountingLLFrame(called_graph, args, lli)
                    #print "folding call", op, "in graph", graph.name
                    try:
                        res = countingframe.eval()
                    except:
                        #print "did not work"
                        pass
                    else:
                        #print "result", res
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
            if op_dont_fold(op):
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
#            if not unchanged:
#                print "doing partial folding in graph", graph.name
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

def iter_op_pairs(graph, opname1, opname2, equality):
    for block in graph.iterblocks():
        num_operations = len(block.operations)
        for current1 in range(num_operations):
            if block.operations[current1].opname != opname1:
                continue
            op1 = block.operations[current1]
            for current2 in range(current1 + 1, num_operations):
                if block.operations[current2].opname != opname2:
                    continue
                op2 = block.operations[current2]
                if equality(op1, op2):
                    yield block, current1, current2
    return

def can_be_same(val1, val2):
    if isinstance(val1, Constant) and isinstance(val2, Constant):
        try:
            return val1.value == val2.value
        except TypeError:
            return False
    return val1.concretetype == val2.concretetype

def remove_getfield(graph, translator):
    """ this removes a getfield after a setfield, if they work on the same
    object and field and if there is no setfield in between which can access
    the same field"""
    def equality(op1, op2):
        if isinstance(op1.args[0], Constant):
            if isinstance(op2.args[0], Constant):
                try:
                    return (op1.args[0].value == op2.args[0].value and
                            op1.args[1].value == op2.args[1].value)
                except TypeError:
                    return False
            return False
        return (op1.args[0] == op2.args[0] and
                op1.args[1].value == op2.args[1].value)
    def remove_if_possible(block, index1, index2):
        op1 = block.operations[index1]
        op2 = block.operations[index2]
        #print "found"
        #print op1
        #print op2
        fieldname = op1.args[1].value
        var_or_const = op1.args[0]
        if op1.opname == "setfield":
            value = op1.args[2]
        else:
            value = op1.result
        for i in range(index1 + 1, index2):
            op = block.operations[i]
            if op.opname == "setfield":
                if op.args[1].value != fieldname:
                    continue
                if can_be_same(op.args[0], op1.args[0]):
                    break
            if op.opname == "direct_call":
                break # giving up for now
            if op.opname == "indirect_call":
                break # giving up for now
        else:
            op2.opname = "same_as"
            op2.args = [value]
            return 1
        return 0
    count = 0
    for block, index1, index2 in iter_op_pairs(
        graph, "setfield", "getfield", equality):
        count += remove_if_possible(block, index1, index2)
    for block, index1, index2 in iter_op_pairs(
        graph, "getfield", "getfield", equality):
        count += remove_if_possible(block, index1, index2)
    if count:
        remove_same_as(graph)
    return count

def remove_all_getfields(graph, t):
    count = 0
    while 1:
        newcount = remove_getfield(graph, t)
        count += newcount
        if not newcount:
            break
    if count:
        log.removegetfield("removed %s getfields in %s" % (count, graph.name))
    return count

def propagate_all_per_graph(graph, translator):
    def prop():
        changed = False
        changed = rewire_links(graph) or changed
        changed = propagate_consts(graph) or changed
#        changed = coalesce_links(graph) or changed
#        changed = do_atmost(100, constant_folding, graph,
#                                       translator) or changed
#        changed = partial_folding(graph, translator) or changed
        changed = remove_all_getfields(graph, translator) or changed
        checkgraph(graph)
        return changed
    do_atmost(10, prop)    

def propagate_all(translator):
    for graph in translator.graphs:
        propagate_all_per_graph(graph, translator)
