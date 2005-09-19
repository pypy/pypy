from pypy.translator.unsimplify import split_block
from pypy.objspace.flow.model import Block, flatten


def create_exception_handling(translator, graph):
    """After an exception in a direct_call, that is not catched by an explicit
    except statement, we need to reraise the exception. So after this
    direct_call we need to test if an exception had occurred. If so, we return
    from the current graph with an unused value (false/0/0.0/null).
    Because of the added exitswitch we need an additional block.
    """
    blocks = [x for x in flatten(graph) if isinstance(x, Block)]
    for block in blocks:
        for i in range(len(block.operations)-1, -1, -1):
            op = block.operations[i]
            if op.opname == 'direct_call':
                split_block(translator, graph, block, i)
