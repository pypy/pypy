import py
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.rmodel import inputconst 
from pypy.tool.ansi_print import ansi_log
from pypy.translator.unsimplify import split_block, copyvar
from pypy.objspace.flow.model import Constant, Variable, SpaceOperation
from pypy.rpython.lltypesystem import lltype

log = py.log.Producer("backendopt")
py.log.setconsumer("backendopt", ansi_log)

def graph_operations(graph):
    for block in graph.iterblocks():
        for op in block.operations: 
            yield op

def all_operations(translator):
    for graph in translator.graphs:
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
    for var in vars:
        TYPE = getattr(var, "concretetype", lltype.Ptr(lltype.PyObject))
        if isinstance(TYPE, lltype.Ptr) and not var_needsgc(var):
            try:
                lltype.castable(TYPE, rclass.CLASSTYPE)
            except lltype.InvalidCast:
                return True
    else:
        return False

def generate_keepalive(vars):
    keepalive_ops = []
    for v in vars:
        if isinstance(v, Constant):
            continue
        if v.concretetype._is_atomic():
            continue
        v_keepalive = Variable()
        v_keepalive.concretetype = lltype.Void
        keepalive_ops.append(SpaceOperation('keepalive', [v], v_keepalive))
    return keepalive_ops

def split_block_with_keepalive(translator, graph, block, index_operation,
                               keep_alive_op_args=True):
    afterblock = split_block(translator, graph, block, index_operation)
    conservative_keepalives = needs_conservative_livevar_calculation(block)
    if conservative_keepalives:
        keep_alive_vars = [var for var in block.getvariables()
                               if var_needsgc(var)]
        # XXX you could maybe remove more, if the variables are kept
        # alive by something else. but this is sometimes hard to know
        for i, var in enumerate(keep_alive_vars):
            try:
                index = block.exits[0].args.index(var)
                newvar = afterblock.inputargs[index]
            except ValueError:
                block.exits[0].args.append(var)
                newvar = copyvar(translator, var)
                afterblock.inputargs.append(newvar)
            keep_alive_vars[i] = newvar
    elif keep_alive_op_args:
        keep_alive_vars = [var for var in afterblock.operations[0].args
                               if var_needsgc(var)]
    else:
        keep_alive_vars = []
    afterblock.operations.extend(generate_keepalive(keep_alive_vars))
    return afterblock

def md5digest(translator):
    import md5
    m = md5.new()
    for op in all_operations(translator):
        m.update(op.opname + str(op.result))
        for a in op.args:
            m.update(str(a))
    return m.digest()[:]
