"""Peephole Flow Graph Transformation
"""

import autopath
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.translator.annotation import Annotator

def transform_allocate(self):
    for block, ann in self.annotated.iteritems():
        operations = block.operations
        n_op = len(operations)
        for i in range(0, n_op-1):
            op1 = operations[i]
            op2 = operations[i+1]
            if (op1.opname == 'newlist' and
                len(op1.args) == 1 and
                op2.opname == 'mul' and
                op1.result is op2.args[0] and
                ann.get_type(op2.args[1]) is int):
                new_op = SpaceOperation('alloc_and_set',
                                        (op2.args[1], op1.args[0]),
                                        op2.result)
                block.operations = (operations[:i] +
                                    (new_op,) +
                                    operations[i+2:])

def transform_slice(self):
    for block, ann in self.annotated.iteritems():
        operations = block.operations
        n_op = len(operations)
        for i in range(0, n_op-1):
            op1 = operations[i]
            op2 = operations[i+1]
            if (op1.opname == 'newslice' and
                ann.get_type(op1.args[2]) is type(None) and
                op2.opname == 'getitem' and
                op1.result is op2.args[1]):
                new_op = SpaceOperation('getslice',
                                         (op2.args[0], op1.args[0], op1.args[1]),
                                         op2.result)
                block.operations = (operations[:i] +
                                    (new_op,) +
                                    operations[i+2:])

def transform_graph(ann):
    transform_allocate(ann)
    transform_slice(ann)
