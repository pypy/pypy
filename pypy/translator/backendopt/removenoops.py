from pypy.objspace.flow.model import Block, Variable, Constant
from pypy.objspace.flow.model import traverse
from pypy.rpython.lltypesystem.lltype import Void

def remove_unaryops(graph, opnames):
    """Removes unary low-level ops with a name appearing in the opnames list.
    """
    positions = []
    def visit(node): 
        if isinstance(node, Block): 
            for i, op in enumerate(node.operations):
                if op.opname in opnames:
                    positions.append((node, i))
    traverse(visit, graph)
    while positions:
        block, index = positions.pop()
        op_result = block.operations[index].result
        op_arg = block.operations[index].args[0]
        # replace the new variable (op_result) with the old variable
        # (from all subsequent positions)
        for op in block.operations[index:]:
            if op is not None:
                for i in range(len(op.args)):
                    if op.args[i] == op_result:
                        op.args[i] = op_arg
        for link in block.exits:
            for i in range(len(link.args)):
                if link.args[i] == op_result:
                    link.args[i] = op_arg
        if block.exitswitch == op_result:
            if isinstance(op_arg, Variable):
                block.exitswitch = op_arg
            else:
                assert isinstance(op_arg, Constant)
                newexits = [link for link in block.exits
                                 if link.exitcase == op_arg.value]
                assert len(newexits) == 1
                newexits[0].exitcase = None
                if hasattr(newexits[0], 'llexitcase'):
                    newexits[0].llexitcase = None
                block.exitswitch = None
                block.recloseblock(*newexits)
        block.operations[index] = None
       
    # remove all operations
    def visit(node): 
        if isinstance(node, Block) and node.operations:
            node.operations[:] = filter(None, node.operations)
    traverse(visit, graph)

def remove_same_as(graph):
    remove_unaryops(graph, ["same_as"])


def remove_void(translator):
    for graph in translator.graphs:
        args = [arg for arg in graph.startblock.inputargs
                    if arg.concretetype is not Void]
        graph.startblock.inputargs = args
        for block in graph.iterblocks():
            for op in block.operations:
                if op.opname in ('direct_call', 'indirect_call'):
                    args = [arg for arg in op.args
                                if arg.concretetype is not Void]
                    op.args = args
 
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
