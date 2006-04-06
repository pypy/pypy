import py
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.rmodel import inputconst 
from pypy.tool.ansi_print import ansi_log

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

def md5digest(translator):
    import md5
    m = md5.new()
    for op in all_operations(translator):
        m.update(op.opname + str(op.result))
        for a in op.args:
            m.update(str(a))
    return m.digest()[:]
