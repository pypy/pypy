import py
from pypy.rpython.lltypesystem.lltype import functionptr, FuncType, typeOf
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
    fptr   = functionptr(FuncType(args, result.concretetype), func.func_name, graph=graph)
    c      = inputconst(typeOf(fptr), fptr) 
    return c
