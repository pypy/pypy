from pypy.objspace.flow.model import Constant, Block, flatten
from pypy.objspace.flow.model import SpaceOperation
from pypy.rpython import lltype

def remove_zero_byte_mallocs(graph):
    blocks = [x for x in flatten(graph) if isinstance(x, Block)]
    for block in blocks:
        for i, op in enumerate(block.operations):
            if op.opname != 'malloc':
                continue
            arg = op.args[0].value
            if True: #isinstance(arg, lltype.Struct) and arg._names_without_voids() == []:
                print 'remove_zero_byte_mallocs: removed malloc(%s) from previous line' % arg
                nullresulttype = op.result.concretetype
                nullresult     = Constant(nullresulttype._defl(), nullresulttype)
                block.operations[i] = SpaceOperation('cast_null_to_ptr', [nullresult], op.result)
