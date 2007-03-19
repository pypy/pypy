from pypy.rpython.ootypesystem import ootype
from pypy.objspace.flow import model as flowmodel

class SubOperation(object):
    def __init__(self, op):
        self.op = op
        self.concretetype = op.result.concretetype

    def __repr__(self):
        return "[%s(%s)]" % (self.op.opname,
                           ", ".join(map(repr, self.op.args)))

def is_mutable(TYPE):
    return isinstance(TYPE, (ootype.Instance,
                             ootype.Record,
                             ootype.List,
                             ootype.Dict,
                             ootype.StringBuilder.__class__,
                             ootype.CustomDict,
                             ootype.DictItemsIterator))

def can_be_inlined(op):
    for v in op.args:
        if isinstance(v, flowmodel.Variable) and is_mutable(v.concretetype):
            return False
    return True

def build_op_map(block):
    var_count = {}
    var_to_op = {}
    def inc(v):
        if isinstance(v, flowmodel.Variable):
            var_count[v] = var_count.get(v, 0) + 1

    for i, op in enumerate(block.operations):
        var_to_op[op.result] = i, op
        for v in op.args:
            inc(v)
    for link in block.exits:
        for v in link.args:
            inc(v)
    return var_count, var_to_op

def build_trees_for_block(block):
    var_count, var_to_op = build_op_map(block)
    for op in block.operations:
        for i, v in enumerate(op.args):
            if var_count.get(v, None) == 1 and v not in block.inputargs: # "inline" the operation
                sub_i, sub_op = var_to_op[v]
                if can_be_inlined(sub_op):
                    op.args[i] = SubOperation(sub_op)
                    block.operations[sub_i] = None
    block.operations = [op for op in block.operations if op is not None]

def build_trees(graph):
    if not getattr(graph, 'tree_built', False):
        for block in graph.iterblocks():
            build_trees_for_block(block)
        graph.tree_built = True
