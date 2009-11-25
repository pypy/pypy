from pypy.rpython.lltypesystem.lloperation import LLOp, LL_OPERATIONS as LL_OPS
from pypy.rpython.ootypesystem import ootype
from pypy.objspace.flow import model as flowmodel

LL_OPERATIONS = {
    'clibox':               LLOp(oo=True, canfold=True),
    'cliunbox':             LLOp(oo=True, canfold=True),
    'cli_newarray':         LLOp(oo=True, canfold=True),
    'cli_getelem':          LLOp(oo=True, sideeffects=False),
    'cli_setelem':          LLOp(oo=True),
    'cli_typeof':           LLOp(oo=True, canfold=True),
    'cli_arraylength':      LLOp(oo=True, canfold=True),
    }
LL_OPERATIONS.update(LL_OPS)

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

# TODO: analyze graphs to determine which functions calls could have
# side effects and which can be inlined safely.
def can_be_inlined(op):
    try:
        llop = LL_OPERATIONS[op.opname]
        return llop.canfold
    except KeyError:
        return False

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
    if block.exitswitch is not None:
        inc(block.exitswitch)
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
    if block.operations != ():
        block.operations = [op for op in block.operations if op is not None]

def build_trees(graph):
    if not getattr(graph, 'tree_built', False):
        for block in graph.iterblocks():
            build_trees_for_block(block)
        graph.tree_built = True
