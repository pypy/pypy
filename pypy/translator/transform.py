"""Flow Graph Transformation

The difference between simplification and transformation is that
transformation may introduce new space operation.
"""

import autopath
import types
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation

# XXX: Lots of duplicated codes. Fix this!

# [a] * b
# -->
# c = newlist(a)
# d = mul(c, int b)
# -->
# d = alloc_and_set(b, a)

def transform_allocate(self):
    """Transforms [a] * b to alloc_and_set(b, a) where b is int."""
    t = self.transaction()
    for block in self.annotated:
        operations = block.operations[:]
        n_op = len(operations)
        for i in range(0, n_op-1):
            op1 = operations[i]
            op2 = operations[i+1]
            if (op1.opname == 'newlist' and
                len(op1.args) == 1 and
                op2.opname == 'mul' and
                op1.result is op2.args[0] and
                t.get_type(self.binding(op2.args[1])) is int):
                new_op = SpaceOperation('alloc_and_set',
                                        (op2.args[1], op1.args[0]),
                                        op2.result)
                block.operations[i:i+2] = [new_op]

# a[b:c]
# -->
# d = newslice(b, c, None)
# e = getitem(a, d)
# -->
# e = getslice(a, b, c)

def transform_slice(self):
    """Transforms a[b:c] to getslice(a, b, c)."""
    t = self.transaction()
    for block in self.annotated:
        operations = block.operations[:]
        n_op = len(operations)
        for i in range(0, n_op-1):
            op1 = operations[i]
            op2 = operations[i+1]
            if (op1.opname == 'newslice' and
                t.get_type(self.binding(op1.args[2])) is types.NoneType and
                op2.opname == 'getitem' and
                op1.result is op2.args[1]):
                new_op = SpaceOperation('getslice',
                                        (op2.args[0], op1.args[0], op1.args[1]),
                                        op2.result)
                block.operations[i:i+2] = [new_op]

# a(*b)
# -->
# c = newtuple(*b)
# d = newdict()
# e = call(function a, c, d)
# -->
# e = simple_call(a, *b)

def transform_simple_call(self):
    """Transforms a(*b) to simple_call(a, *b)"""
    t = self.transaction()
    for block in self.annotated:
        operations = block.operations[:]
        n_op = len(operations)
        for i in range(0, n_op-2):
            op1 = operations[i]
            op2 = operations[i+1]
            op3 = operations[i+2]
            if not op3.args: continue
            op3arg0type = t.get_type(self.binding(op3.args[0]))
            if (op1.opname == 'newtuple' and
                op2.opname == 'newdict' and
                len(op2.args) == 0 and
                op3.opname == 'call' and
                op1.result is op3.args[1] and
                op2.result is op3.args[2] and
                # eek!
                (op3arg0type is types.FunctionType or
                 op3arg0type is types.BuiltinFunctionType)):
                new_op = SpaceOperation('simple_call',
                                        (op3.args[0],) + tuple(op1.args),
                                        op3.result)
                block.operations[i:i+3] = [new_op]

def transform_graph(ann):
    """Apply set of transformations available."""
    transform_allocate(ann)
    transform_slice(ann)
    transform_simple_call(ann)
