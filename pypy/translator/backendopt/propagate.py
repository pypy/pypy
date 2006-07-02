from pypy.objspace.flow.model import Block, Variable, Constant, c_last_exception
from pypy.objspace.flow.model import traverse, mkentrymap, checkgraph
from pypy.objspace.flow.model import SpaceOperation, Link
from pypy.rpython.lltypesystem import lltype, lloperation
from pypy.rpython.llinterp import LLInterpreter, LLFrame
from pypy.translator import simplify
from pypy.translator.simplify import get_graph
from pypy.translator.unsimplify import copyvar
from pypy.translator.backendopt.removenoops import remove_same_as
from pypy.translator.backendopt.inline import OP_WEIGHTS
from pypy.translator.backendopt.ssa import DataFlowFamilyBuilder
from pypy.translator.backendopt.support import log, var_needsgc
from pypy.translator.backendopt.graphanalyze import GraphAnalyzer

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

class CanfoldAnalyzer(GraphAnalyzer):
    def operation_is_true(self, op):
        if op.opname in ('getfield', 'getarrayitem'):
            CONTAINER = op.args[0].concretetype.TO
            if CONTAINER._hints.get('immutable'):
                return False
        if op.opname in ("getsubstruct", "getarraysubstruct",
                         "direct_fieldptr", "direct_arrayitems"):
            # this is needed so that the parent of the result (op.args[0])
            # does not go away after the op is folded. see test_dont_fold_getsubstruct
            if not var_needsgc(op.result):
                # if the containing object is immortal, one can still fold:
                if isinstance(op.args[0], Constant) and op.args[0].value._solid:
                    return False
                return True
        try:
            return not lloperation.LL_OPERATIONS[op.opname].canfold
        except KeyError:
            return True

def constant_folding(graph, translator, analyzer=None):
    """do constant folding if the arguments of an operations are constants"""
    if analyzer is None:
        analyzer = CanfoldAnalyzer(translator)
    lli = LLInterpreter(translator.rtyper, tracing=False)
    llframe = LLFrame(graph, None, lli)
    changed = False
    for block in graph.iterblocks():
        for i, op in enumerate(block.operations):
            if sum([isinstance(arg, Variable) for arg in op.args]):
                continue
            # don't fold stuff with exception handling
            if (block.exitswitch == c_last_exception and
                i == len(block.operations) - 1):
                continue
            if analyzer.analyze(op):
                continue
            try:
                if op.opname == "direct_call":
                    called_graph = get_graph(op.args[0], translator)
                    args = [arg.value for arg in op.args[1:]]
                    countingframe = CountingLLFrame(called_graph, args, lli)
                    res = Constant(countingframe.eval())
                else:
                    llframe.eval_operation(op)
                    res = Constant(llframe.getval(op.result))
            except (SystemExit, KeyboardInterrupt):
                raise
            except:    # XXXXXXXXXXXXXXXX try to only catch TypeError
                continue
            log.constantfolding("in graph %s, %s = %s" %
                                (graph.name, op, res))
            res.concretetype = op.result.concretetype
            block.operations[i].opname = "same_as"
            block.operations[i].args = [res]
            changed = True
    if changed:
        remove_same_as(graph)
        propagate_consts(graph)
        checkgraph(graph)
        return True
    return False

#def partial_folding_once(graph, translator, analyzer=None):
#    if analyzer is None:
#        analyzer = CanfoldAnalyzer(translator)
#    lli = LLInterpreter(translator.rtyper)
#    entrymap = mkentrymap(graph)
#    for block in graph.iterblocks():
#        if (block is graph.startblock or block is graph.returnblock or
#            block is graph.exceptblock):
#            continue
#        usedvars = {}
#        cannotfold = False
#        for op in block.operations:
#            if analyzer.analyze(op):
#                cannotfold = True
#                break
#            for arg in op.args:
#                if (isinstance(arg, Variable) and arg in block.inputargs):
#                    usedvars[arg] = True
#        if cannotfold:
#            continue
#        if isinstance(block.exitswitch, Variable):
#            usedvars[block.exitswitch] = True
#        pattern = [arg in usedvars for arg in block.inputargs]
#        for link in entrymap[block]:
#            s = sum([isinstance(arg, Constant) or not p
#                         for arg, p in zip(link.args, pattern)])
#            if s != len(link.args):
#                continue
#            args = []
#            for i, arg in enumerate(link.args):
#                if isinstance(arg, Constant):
#                    args.append(arg.value)
#                else:
#                    assert not pattern[i]
#                    args.append(arg.concretetype._example())
#            llframe = LLFrame(graph, None, lli)
#            llframe.fillvars(block, args)
#            nextblock, forwardargs = llframe.eval_block(block)
#            if nextblock is not None:
#                newargs = []
#                for i, arg in enumerate(nextblock.inputargs):
#                    try:
#                        index = [l.target for l in block.exits].index(nextblock)
#                        index = block.inputargs.index(block.exits[index].args[i])
#                    except ValueError:
#                        c = Constant(forwardargs[i])
#                        c.concretetype = arg.concretetype
#                        newargs.append(c)
#                    else:
#                        newargs.append(link.args[index])
#            else:
#                assert 0, "this should not occur"
#            unchanged = link.target == nextblock and link.args == newargs
#            link.target = nextblock
#            link.args = newargs
#            checkgraph(graph)
#            if not unchanged:
#                return True
#    return False

def partial_folding_once(graph, translator, analyzer=None):
    # XXX this is quite a suboptimal way to do it, but was easy to program
    if analyzer is None:
        analyzer = CanfoldAnalyzer(translator)
    lli = LLInterpreter(translator.rtyper)
    entrymap = mkentrymap(graph)
    for block, links in entrymap.iteritems():
        # identify candidates
        for link in links:
            available_vars = {}
            foldable_ops = {}
            for i, arg in enumerate(link.args):
                if isinstance(arg, Constant):
                    available_vars[block.inputargs[i]] = True
            if not available_vars:
                continue
            for op in block.operations:
                if analyzer.analyze(op):
                    continue
                for arg in op.args:
                    if not (isinstance(arg, Constant) or arg in available_vars):
                        break
                else:
                    foldable_ops[op] = True
                    available_vars[op.result] = True
            if not foldable_ops:
                continue
            # the link is a candidate. copy the target block so that
            # constant folding can do its work
            # whew, copying is annoying :-(. XXX nicely factor this out
            vars_to_newvars = {}
            def getnewvar(var):
                if var in vars_to_newvars:
                    return vars_to_newvars[var]
                if var is None:
                    return None
                if isinstance(var, Constant):
                    return var
                result = copyvar(None, var)
                vars_to_newvars[var] = result
                return result
            newops = []
            for op in block.operations:
                newargs = [getnewvar(var) for var in op.args]
                newresult = getnewvar(op.result)
                newops.append(SpaceOperation(op.opname, newargs, newresult))
            newargs = [getnewvar(var) for var in block.inputargs]
            newblock = Block(newargs)
            newblock.exitswitch = getnewvar(block.exitswitch)
            newblock.operations = newops
            newlinks = []
            for copylink in block.exits:
                newargs = [getnewvar(var) for var in copylink.args]
                newlink = Link(newargs, copylink.target, copylink.exitcase)
                newlink.prevblock = block
                newlink.last_exception = getnewvar(copylink.last_exception)
                newlink.last_exc_value = getnewvar(copylink.last_exc_value)
                if hasattr(link, 'llexitcase'):
                    newlink.llexitcase = link.llexitcase
                newlinks.append(newlink)
            newblock.closeblock(*newlinks)
            link.target = newblock
    propagate_consts(graph)
    result = constant_folding(graph, translator, analyzer)
    if result:
        simplify.join_blocks(graph)
    return result

def partial_folding(graph, translator, analyzer=None):
    if do_atmost(1000, partial_folding_once, graph, translator, analyzer):
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
        analyzer = CanfoldAnalyzer(translator)
        changed = False
        changed = rewire_links(graph) or changed
        changed = propagate_consts(graph) or changed
        changed = coalesce_links(graph) or changed
        changed = do_atmost(100, constant_folding, graph,
                                       translator, analyzer) or changed
        changed = partial_folding(graph, translator, analyzer) or changed
        changed = remove_all_getfields(graph, translator) or changed
        checkgraph(graph)
        return changed
    do_atmost(10, prop)    

def propagate_all(translator):
    for graph in translator.graphs:
        propagate_all_per_graph(graph, translator)
