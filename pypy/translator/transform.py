"""Flow Graph Transformation

The difference between simplification and transformation is that
transformation may introduce new space operation.
"""

import autopath
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.translator.annotation import Annotator

# b = newlist(a)
# d = mul(b, int c)
# --> d = alloc_and_set(c, a)

def transform_allocate(self):
    """Transforms [a] * b to alloc_and_set(b, a) where b is int."""
    for block, ann in self.annotated.iteritems():
        operations = block.operations[:]
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
                block.operations[i:i+2] = [new_op]

# c = newslice(a, b, None)
# e = getitem(d, c)
# --> e = getslice(d, a, b)

def transform_slice(self):
    """Transforms a[b:c] to getslice(a, b, c)."""
    for block, ann in self.annotated.iteritems():
        operations = block.operations[:]
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
                block.operations[i:i+2] = [new_op]

def transform_graph(ann):
    """Apply set of transformations available."""
    transform_allocate(ann)
    transform_slice(ann)
