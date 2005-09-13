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

def remove_same_as(graph):
    """Remove all 'same_as' operations.
    """
    same_as_positions = []
    def visit(node): 
        if isinstance(node, Block): 
            for i, op in enumerate(node.operations):
                if op.opname == 'same_as': 
                    same_as_positions.append((node, i))
    traverse(visit, graph)
    while same_as_positions:
        block, index = same_as_positions.pop()
        same_as_result = block.operations[index].result
        same_as_arg = block.operations[index].args[0]
        # replace the new variable (same_as_result) with the old variable
        # (from all subsequent positions)
        for op in block.operations[index:]:
            if op is not None:
                for i in range(len(op.args)):
                    if op.args[i] == same_as_result:
                        op.args[i] = same_as_arg
        for link in block.exits:
            for i in range(len(link.args)):
                if link.args[i] == same_as_result:
                    link.args[i] = same_as_arg
        if block.exitswitch == same_as_result:
            block.exitswitch = same_as_arg
        block.operations[index] = None
       
    # remove all same_as operations
    def visit(node): 
        if isinstance(node, Block) and node.operations:
            node.operations[:] = filter(None, node.operations)
    traverse(visit, graph)


def remove_void(translator):
    for func, graph in translator.flowgraphs.iteritems():
        args = [arg for arg in graph.startblock.inputargs
                    if arg.concretetype is not Void]
        graph.startblock.inputargs = args
    def visit(block): 
        if isinstance(block, Block):
            for op in block.operations:
                if op.opname == 'direct_call':
                    args = [arg for arg in op.args
                                if arg.concretetype is not Void]
                    op.args = args
    for func, graph in translator.flowgraphs.iteritems():
        traverse(visit, graph)
 
##def rename_extfunc_calls(translator):
##    from pypy.rpython.extfunctable import table as extfunctable
##    def visit(block): 
##        if isinstance(block, Block):
##            for op in block.operations:
##                if op.opname != 'direct_call':
##                    continue
##                functionref = op.args[0]
##                if not isinstance(functionref, Constant):
##                    continue
##                _callable = functionref.value._obj._callable
##                for func, extfuncinfo in extfunctable.iteritems():  # precompute a dict?
##                    if _callable is not extfuncinfo.ll_function or not extfuncinfo.backend_functiontemplate:
##                        continue
##                    language, functionname = extfuncinfo.backend_functiontemplate.split(':')
##                    if language is 'C':
##                        old_name = functionref.value._obj._name[:]
##                        functionref.value._obj._name = functionname
##                        #print 'rename_extfunc_calls: %s -> %s' % (old_name, functionref.value._obj._name)
##                        break
##    for func, graph in translator.flowgraphs.iteritems():
##        traverse(visit, graph)
