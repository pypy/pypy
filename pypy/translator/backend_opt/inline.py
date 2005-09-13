##from pypy.translator.translator import Translator
##from pypy.translator.simplify import eliminate_empty_blocks, join_blocks
##from pypy.translator.simplify import remove_identical_vars
##from pypy.translator.simplify import transform_dead_op_vars
##from pypy.translator.unsimplify import copyvar, split_block
##from pypy.objspace.flow.model import Variable, Constant, Block, Link
##from pypy.objspace.flow.model import SpaceOperation, last_exception
##from pypy.objspace.flow.model import traverse, mkentrymap, checkgraph
##from pypy.annotation import model as annmodel
##from pypy.tool.unionfind import UnionFind
##from pypy.rpython.lltype import Void, Bool
##from pypy.rpython import rmodel, lltype
from pypy.translator.backend_opt import matfunc

def collect_called_functions(graph):
    funcs = {}
    def visit(obj):
        if not isinstance(obj, Block):
            return
        for op in obj.operations:
            if op.opname == "direct_call":
                funcs[op.args[0]] = True
    traverse(visit, graph)
    return funcs

def inline_function(translator, inline_func, graph):
    count = 0
    callsites = []
    def find_callsites(block):
        if isinstance(block, Block):
            for i, op in enumerate(block.operations):
                if not (op.opname == "direct_call" and
                    isinstance(op.args[0], Constant)):
                    continue
                funcobj = op.args[0].value._obj
                # accept a function or a graph as 'inline_func'
                if (getattr(funcobj, 'graph', None) is inline_func or
                    getattr(funcobj, '_callable', None) is inline_func):
                    callsites.append((block, i))
    traverse(find_callsites, graph)
    while callsites != []:
        block, index_operation = callsites.pop()
        _inline_function(translator, graph, block, index_operation)
        callsites = []
        traverse(find_callsites, graph)
        checkgraph(graph)
        count += 1
    return count

def _find_exception_type(block):
    #XXX slightly brittle: find the exception type for simple cases
    #(e.g. if you do only raise XXXError) by doing pattern matching
    ops = block.operations
    if (len(ops) < 6 or
        ops[-6].opname != "malloc" or ops[-5].opname != "cast_pointer" or
        ops[-4].opname != "setfield" or ops[-3].opname != "cast_pointer" or
        ops[-2].opname != "getfield" or ops[-1].opname != "cast_pointer" or
        len(block.exits) != 1 or block.exits[0].args[0] != ops[-2].result or
        block.exits[0].args[1] != ops[-1].result or
        not isinstance(ops[-4].args[1], Constant) or
        ops[-4].args[1].value != "typeptr"):
        return None
    return ops[-4].args[2].value

def _inline_function(translator, graph, block, index_operation):
    op = block.operations[index_operation]
    graph_to_inline = op.args[0].value._obj.graph
    exception_guarded = False
    if (block.exitswitch == Constant(last_exception) and
        index_operation == len(block.operations) - 1):
        exception_guarded = True
        if len(collect_called_functions(graph_to_inline)) != 0:
            raise NotImplementedError("can't handle exceptions yet")
    entrymap = mkentrymap(graph_to_inline)
    beforeblock = block
    afterblock = split_block(translator, graph, block, index_operation)
    assert afterblock.operations[0] is op
    #vars that need to be passed through the blocks of the inlined function
    passon_vars = {beforeblock: [arg for arg in beforeblock.exits[0].args
                                     if isinstance(arg, Variable)]}
    copied_blocks = {}
    varmap = {}
    def get_new_name(var):
        if var is None:
            return None
        if isinstance(var, Constant):
            return var
        if var not in varmap:
            varmap[var] = copyvar(translator, var)
        return varmap[var]
    def get_new_passon_var_names(block):
        result = [copyvar(translator, var) for var in passon_vars[beforeblock]]
        passon_vars[block] = result
        return result
    def copy_operation(op):
        args = [get_new_name(arg) for arg in op.args]
        return SpaceOperation(op.opname, args, get_new_name(op.result))
    def copy_block(block):
        if block in copied_blocks:
            "already there"
            return copied_blocks[block]
        args = ([get_new_name(var) for var in block.inputargs] +
                get_new_passon_var_names(block))
        newblock = Block(args)
        copied_blocks[block] = newblock
        newblock.operations = [copy_operation(op) for op in block.operations]
        newblock.exits = [copy_link(link, block) for link in block.exits]
        newblock.exitswitch = get_new_name(block.exitswitch)
        newblock.exc_handler = block.exc_handler
        return newblock
    def copy_link(link, prevblock):
        newargs = [get_new_name(a) for a in link.args] + passon_vars[prevblock]
        newlink = Link(newargs, copy_block(link.target), link.exitcase)
        newlink.prevblock = copy_block(link.prevblock)
        newlink.last_exception = get_new_name(link.last_exception)
        newlink.last_exc_value = get_new_name(link.last_exc_value)
        if hasattr(link, 'llexitcase'):
            newlink.llexitcase = link.llexitcase
        return newlink
    linktoinlined = beforeblock.exits[0]
    assert linktoinlined.target is afterblock
    copiedstartblock = copy_block(graph_to_inline.startblock)
    copiedstartblock.isstartblock = False
    copiedreturnblock = copied_blocks[graph_to_inline.returnblock]
    #find args passed to startblock of inlined function
    passon_args = []
    for arg in op.args[1:]:
        if isinstance(arg, Constant):
            passon_args.append(arg)
        else:
            index = afterblock.inputargs.index(arg)
            passon_args.append(linktoinlined.args[index])
    passon_args += passon_vars[beforeblock]
    #rewire blocks
    linktoinlined.target = copiedstartblock
    linktoinlined.args = passon_args
    afterblock.inputargs = [op.result] + afterblock.inputargs
    afterblock.operations = afterblock.operations[1:]
    linkfrominlined = Link([copiedreturnblock.inputargs[0]] + passon_vars[graph_to_inline.returnblock], afterblock)
    linkfrominlined.prevblock = copiedreturnblock
    copiedreturnblock.exitswitch = None
    copiedreturnblock.exits = [linkfrominlined]
    assert copiedreturnblock.exits[0].target == afterblock
    if graph_to_inline.exceptblock in entrymap:
        #let links to exceptblock of the graph to inline go to graphs exceptblock
        copiedexceptblock = copied_blocks[graph_to_inline.exceptblock]
        if not exception_guarded:
            copiedexceptblock = copied_blocks[graph_to_inline.exceptblock]
            for link in entrymap[graph_to_inline.exceptblock]:
                copiedblock = copied_blocks[link.prevblock]
                assert len(copiedblock.exits) == 1
                copiedblock.exits[0].args = copiedblock.exits[0].args[:2]
                copiedblock.exits[0].target = graph.exceptblock
        else:
            def find_args_in_exceptional_case(link, block, etype, evalue):
                linkargs = []
                for arg in link.args:
                    if arg == link.last_exception:
                        linkargs.append(etype)
                    elif arg == link.last_exc_value:
                        linkargs.append(evalue)
                    elif isinstance(arg, Constant):
                        linkargs.append(arg)
                    else:
                        index = afterblock.inputargs.index(arg)
                        linkargs.append(passon_vars[block][index - 1])
                return linkargs
            exc_match = Constant(rmodel.getfunctionptr(
                translator,
                translator.rtyper.getexceptiondata().ll_exception_match))
            #try to match the exceptions for simple cases
            for link in entrymap[graph_to_inline.exceptblock]:
                copiedblock = copied_blocks[link.prevblock]
                copiedlink = copiedblock.exits[0]
                eclass = _find_exception_type(copiedblock)
                #print copiedblock.operations
                if eclass is None:
                    continue
                etype = copiedlink.args[0]
                evalue = copiedlink.args[1]
                for exceptionlink in afterblock.exits[1:]:
                    if exc_match.value(eclass, exceptionlink.llexitcase):
                        copiedlink.target = exceptionlink.target
                        linkargs = find_args_in_exceptional_case(exceptionlink,
                                                                 link.prevblock,
                                                                 etype, evalue)
                        copiedlink.args = linkargs
                        break
            #XXXXX don't look: insert blocks that do exception matching
            #for the cases where direct matching did not work
            blocks = []
            for i, link in enumerate(afterblock.exits[1:]):
                etype = copyvar(translator, copiedexceptblock.inputargs[0])
                evalue = copyvar(translator, copiedexceptblock.inputargs[1])
                block = Block([etype, evalue] + get_new_passon_var_names(link.target))
                res = Variable()
                res.concretetype = Bool
                translator.annotator.bindings[res] = annmodel.SomeBool()
                args = [exc_match, etype, Constant(link.llexitcase)]
                block.operations.append(SpaceOperation("direct_call", args, res))
                block.exitswitch = res
                linkargs = find_args_in_exceptional_case(link, link.target,
                                                         etype, evalue)
                l = Link(linkargs, link.target)
                l.prevblock = block
                l.exitcase = True
                block.exits.append(l)
                if i > 0:
                    l = Link(blocks[-1].inputargs, block)
                    l.prevblock = blocks[-1]
                    l.exitcase = False
                    blocks[-1].exits.insert(0, l)
                blocks.append(block)
            blocks[-1].exits = blocks[-1].exits[:1]
            blocks[-1].operations = []
            blocks[-1].exitswitch = None
            linkargs = copiedexceptblock.inputargs
            copiedexceptblock.closeblock(Link(linkargs, blocks[0]))
            afterblock.exits = [afterblock.exits[0]]
            afterblock.exitswitch = None
    #cleaning up -- makes sense to be here, because I insert quite
    #some empty blocks and blocks that can be joined
    eliminate_empty_blocks(graph)
    join_blocks(graph)
    remove_identical_vars(graph)

# ____________________________________________________________
#
# Automatic inlining

def measure_median_execution_cost(graph):
    linktargets = [graph.startblock]
    linkmap = {}
    for node in flatten(graph):
        if isinstance(node, Link):
            linkmap[node] = len(linktargets)
            linktargets.append(node.target)
    matrix = []
    vector = []
    for i, target in zip(range(len(linktargets)), linktargets):
        vector.append(len(target.operations))
        row = [0.0] * len(linktargets)
        row[i] = 1.0
        if target.exits:
            f = 1.0 / len(target.exits)
            for nextlink in target.exits:
                row[linkmap[nextlink]] -= f
        matrix.append(row)
    M = matfunc.Mat(matrix)
    V = matfunc.Vec(vector)
    # we must solve: M * (vector x1...xn) = V
    try:
        Solution = M._solve(V)
    except (OverflowError, ValueError):
        return sys.maxint
    else:
        return Solution[0]

def static_instruction_count(graph):
    count = 0
    for node in flatten(graph):
        if isinstance(node, Block):
            count += len(node.operations)
    return count

def inlining_heuristic(graph):
    # XXX ponderation factors?
    return (0.819487132 * measure_median_execution_cost(graph) +
            static_instruction_count(graph))


def static_callers(translator):
    result = []
    def build_call_graph(node):
        if isinstance(node, Block):
            for op in node.operations:
                if (op.opname == "direct_call" and
                    isinstance(op.args[0], Constant)):
                    funcobj = op.args[0].value._obj
                    graph = getattr(funcobj, 'graph', None)
                    if graph is not None:
                        result.append((parentgraph, graph))
    for parentgraph in translator.flowgraphs.itervalues():
        traverse(build_call_graph, parentgraph)
    return result


def auto_inlining(translator, threshold=20):
    from heapq import heappop, heapreplace
    callers = {}     # {graph: {graphs-that-call-it}}
    callees = {}     # {graph: {graphs-that-it-calls}}
    for graph1, graph2 in static_callers(translator):
        callers.setdefault(graph2, {})[graph1] = True
        callees.setdefault(graph1, {})[graph2] = True
    fiboheap = [(0.0, graph) for graph in callers]
    valid_weight = {}

    while fiboheap:
        weight, graph = fiboheap[0]
        if not valid_weight.get(graph):
            weight = inlining_heuristic(graph)
            print '  + cost %7.2f %50s' % (weight, graph.name)
            heapreplace(fiboheap, (weight, graph))
            valid_weight[graph] = True
            continue

        if weight >= threshold:
            break   # finished

        heappop(fiboheap)
        print 'Inlining %7.2f %50s' % (weight, graph.name)
        for parentgraph in callers[graph]:
            if parentgraph == graph:
                continue
            print '\t\t-> in %s' % parentgraph.name
            try:
                if backendoptimization.inline_function(translator, graph,
                                                       parentgraph):
                    valid_weight[parentgraph] = False
                    for graph2 in callees.get(graph, {}):
                        callees[parentgraph][graph2] = True
                        callers[graph2][parentgraph] = True
            except NotImplementedError:
                pass
