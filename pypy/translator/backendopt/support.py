import py
from pypy.rpython.lltypesystem import lltype
from pypy.translator.simplify import get_graph
from pypy.rpython.rmodel import inputconst 
from pypy.tool.ansi_print import ansi_log
from pypy.annotation.model import setunion, s_ImpossibleValue
from pypy.translator.unsimplify import split_block, copyvar, insert_empty_block
from pypy.objspace.flow.model import Constant, Variable, SpaceOperation, c_last_exception
from pypy.rpython.lltypesystem import lltype


log = py.log.Producer("backendopt")
py.log.setconsumer("backendopt", ansi_log)


def graph_operations(graph):
    for block in graph.iterblocks():
        for op in block.operations: 
            yield op

def all_operations(graphs):
    for graph in graphs:
        for block in graph.iterblocks():
            for op in block.operations: 
                yield op

def annotate(translator, func, result, args):
    args   = [arg.concretetype for arg in args]
    graph  = translator.rtyper.annotate_helper(func, args)
    fptr   = lltype.functionptr(lltype.FuncType(args, result.concretetype), func.func_name, graph=graph)
    c      = inputconst(lltype.typeOf(fptr), fptr) 
    return c

def var_needsgc(var):
    if hasattr(var, 'concretetype'):
        vartype = var.concretetype
        return isinstance(vartype, lltype.Ptr) and vartype._needsgc()
    else:
        # assume PyObjPtr
        return True

def needs_conservative_livevar_calculation(block):
    from pypy.rpython.lltypesystem import rclass
    vars = block.getvariables()
    assert len(block.exits) == 1
    exitingvars = block.exits[0].args
    for var in vars:
        TYPE = getattr(var, "concretetype", lltype.Ptr(lltype.PyObject))
        if isinstance(TYPE, lltype.Ptr) and not var_needsgc(var):
            if isinstance(TYPE.TO, lltype.FuncType):
                continue
            try:
                lltype.castable(TYPE, rclass.CLASSTYPE)
            except lltype.InvalidCast:
                if var in exitingvars:
                    return True
    else:
        return False

def generate_keepalive(vars, annotator=None):
    keepalive_ops = []
    for v in vars:
        if isinstance(v, Constant):
            continue
        if v.concretetype._is_atomic():
            continue
        v_keepalive = Variable()
        v_keepalive.concretetype = lltype.Void
        if annotator is not None:
            annotator.setbinding(v_keepalive, s_ImpossibleValue)
        keepalive_ops.append(SpaceOperation('keepalive', [v], v_keepalive))
    return keepalive_ops

def split_block_with_keepalive(block, index_operation,
                               keep_alive_op_args=True,
                               annotator=None):
    splitlink = split_block(annotator, block, index_operation)
    afterblock = splitlink.target
    conservative_keepalives = needs_conservative_livevar_calculation(block)
    if conservative_keepalives:
        keep_alive_vars = [var for var in block.getvariables()
                               if var_needsgc(var)]
        # XXX you could maybe remove more, if the variables are kept
        # alive by something else. but this is sometimes hard to know
        for i, var in enumerate(keep_alive_vars):
            try:
                index = splitlink.args.index(var)
                newvar = afterblock.inputargs[index]
            except ValueError:
                splitlink.args.append(var)
                newvar = copyvar(annotator, var)
                afterblock.inputargs.append(newvar)
            keep_alive_vars[i] = newvar
    elif keep_alive_op_args and afterblock.operations: 
        keep_alive_vars = [var for var in afterblock.operations[0].args
                               if isinstance(var, Variable) and var_needsgc(var)]
        if len(afterblock.operations) > 1 or afterblock.exitswitch != c_last_exception:
            afterblock.operations[1:1] = generate_keepalive(keep_alive_vars,
                                                            annotator=annotator)
            keep_alive_vars = []
    else:
        keep_alive_vars = []
    pos = len(afterblock.operations)
    if afterblock.exitswitch == c_last_exception:
        pos -= 1    # insert the keepalives just before the last operation
                    # in case of exception-catching
    afterblock.operations[pos:pos] = generate_keepalive(keep_alive_vars)
    return splitlink

def find_calls_from(translator, graph):
    for block in graph.iterblocks():
        for op in block.operations:
            if op.opname == "direct_call":
                called_graph = get_graph(op.args[0], translator)
                if called_graph is not None:
                    yield block, called_graph
            if op.opname == "indirect_call":
                graphs = op.args[-1].value
                if graphs is not None:
                    for called_graph in graphs:
                        yield block, called_graph

def find_backedges(graph, block=None, seen=None, seeing=None):
    """finds the backedges in the flow graph"""
    backedges = []
    if block is None:
        block = graph.startblock
    if seen is None:
        seen = {block: None}
    if seeing is None:
        seeing = {}
    seeing[block] = True
    for link in block.exits:
        if link.target in seen:
            if link.target in seeing:
                backedges.append(link)
        else:
            seen[link.target] = None
            backedges.extend(find_backedges(graph, link.target, seen, seeing))
    del seeing[block]
    return backedges

def compute_reachability(graph):
    reachable = {}
    blocks = list(graph.iterblocks())
    for block in py.builtin.reversed(blocks): # this order should make the reuse path more likely
        reach = {}
        scheduled = [block]
        while scheduled:
            current = scheduled.pop()
            for link in current.exits:
                if link.target in reachable:
                    reach[link.target] = True
                    reach = setunion(reach, reachable[link.target])
                    continue
                if link.target not in reach:
                    reach[link.target] = True
                    scheduled.append(link.target)
        reachable[block] = reach
    return reachable

def find_loop_blocks(graph):
    """find the blocks in a graph that are part of a loop"""
    loop = {}
    reachable = compute_reachability(graph)
    for backedge in find_backedges(graph):
        start = backedge.target
        end = backedge.prevblock
        loop[start] = start
        loop[end] = start
        scheduled = [start]
        seen = {}
        while scheduled:
            current = scheduled.pop()
            connects = end in reachable[current]
            seen[current] = True
            if connects:
                loop[current] = start
            for link in current.exits:
                if link.target not in seen:
                    scheduled.append(link.target)
    return loop

def md5digest(translator):
    from pypy.tool.compat import md5
    graph2digest = {}
    for graph in translator.graphs:
        m = md5.new()
        for op in graph_operations(graph):
            m.update(op.opname + str(op.result))
            for a in op.args:
                m.update(str(a))
        graph2digest[graph.name] = m.digest()
    return graph2digest
