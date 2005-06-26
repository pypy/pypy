"""Flow Graph Transformation

The difference between simplification and transformation is that
transformation is based on annotations; it runs after the annotator
completed.
"""

from __future__ import generators

import types
from pypy.objspace.flow.model import SpaceOperation
from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import last_exception, checkgraph
from pypy.translator.annrpython import CannotSimplify
from pypy.annotation import model as annmodel
from pypy.annotation.specialize import MemoTable


def checkgraphs(self, blocks):
    for block in blocks:
        fn = self.annotated[block]
        graph = self.translator.flowgraphs[fn]
        checkgraph(graph)

def fully_annotated_blocks(self):
    """Ignore blocked blocks."""
    for block, is_annotated in self.annotated.iteritems():
        if is_annotated:
            yield block

# XXX: Lots of duplicated codes. Fix this!

# [a] * b
# -->
# c = newlist(a)
# d = mul(c, int b)
# -->
# d = alloc_and_set(b, a)

def transform_allocate(self, block_subset):
    """Transforms [a] * b to alloc_and_set(b, a) where b is int."""
    for block in block_subset:
        length1_lists = {}   # maps 'c' to 'a', in the above notation
        for i in range(len(block.operations)):
            op = block.operations[i]
            if (op.opname == 'newlist' and
                len(op.args) == 1):
                length1_lists[op.result] = op.args[0]
            elif (op.opname == 'mul' and
                  op.args[0] in length1_lists and
                  self.gettype(op.args[1]) is int):
                new_op = SpaceOperation('alloc_and_set',
                                        (op.args[1], length1_lists[op.args[0]]),
                                        op.result)
                block.operations[i] = new_op

# a[b:c]
# -->
# d = newslice(b, c, None)
# e = getitem(a, d)
# -->
# e = getslice(a, b, c)

def transform_slice(self, block_subset):
    """Transforms a[b:c] to getslice(a, b, c)."""
    for block in block_subset:
        operations = block.operations[:]
        n_op = len(operations)
        for i in range(0, n_op-1):
            op1 = operations[i]
            op2 = operations[i+1]
            if (op1.opname == 'newslice' and
                self.gettype(op1.args[2]) is types.NoneType and
                op2.opname == 'getitem' and
                op1.result is op2.args[1]):
                new_op = SpaceOperation('getslice',
                                        (op2.args[0], op1.args[0], op1.args[1]),
                                        op2.result)
                block.operations[i+1:i+2] = [new_op]

def transform_dead_op_vars(self, block_subset):
    # we redo the same simplification from simplify.py,
    # to kill dead (never-followed) links,
    # which can possibly remove more variables.
    from pypy.translator.simplify import transform_dead_op_vars_in_blocks
    transform_dead_op_vars_in_blocks(block_subset)

def transform_dead_code(self, block_subset):
    """Remove dead code: these are the blocks that are not annotated at all
    because the annotation considered that no conditional jump could reach
    them."""
    for block in block_subset:
        for link in block.exits:
            if link not in self.links_followed:
                lst = list(block.exits)
                lst.remove(link)
                block.exits = tuple(lst)
                if not block.exits:
                    # oups! cannot reach the end of this block
                    cutoff_alwaysraising_block(self, block)
                elif block.exitswitch == Constant(last_exception):
                    # exceptional exit
                    if block.exits[0].exitcase is not None:
                        # killed the non-exceptional path!
                        cutoff_alwaysraising_block(self, block)
                if len(block.exits) == 1:
                    block.exitswitch = None
                    block.exits[0].exitcase = None

def cutoff_alwaysraising_block(self, block):
    "Fix a block whose end can never be reached at run-time."
    # search the operation that cannot succeed
    can_succeed    = [op for op in block.operations
                         if op.result in self.bindings]
    cannot_succeed = [op for op in block.operations
                         if op.result not in self.bindings]
    n = len(can_succeed)
    # check consistency
    assert can_succeed == block.operations[:n]
    assert cannot_succeed == block.operations[n:]
    assert 0 <= n < len(block.operations)
    # chop off the unreachable end of the block
    del block.operations[n+1:]
    s_impossible = annmodel.SomeImpossibleValue()
    self.bindings[block.operations[n].result] = s_impossible
    # insert the equivalent of 'raise AssertionError'
    # XXX no sane way to get the graph from the block!
    fn = self.annotated[block]
    assert fn in self.translator.flowgraphs, (
        "Cannot find the graph that this block belong to! "
        "fn=%r" % (fn,))
    graph = self.translator.flowgraphs[fn]
    msg = "Call to %r should have raised an exception" % (fn,)
    c1 = Constant(AssertionError)
    c2 = Constant(AssertionError(msg))
    errlink = Link([c1, c2], graph.exceptblock)
    block.recloseblock(errlink, *block.exits)
    # record new link to make the transformation idempotent
    self.links_followed[errlink] = True
    # fix the annotation of the exceptblock.inputargs
    etype, evalue = graph.exceptblock.inputargs
    s_type = annmodel.SomeObject()
    s_type.knowntype = type
    s_type.is_type_of = [evalue]
    s_value = annmodel.SomeInstance(self.bookkeeper.getclassdef(Exception))
    self.setbinding(etype, s_type)
    self.setbinding(evalue, s_value)
    # make sure the bookkeeper knows about AssertionError
    self.bookkeeper.getclassdef(AssertionError)

def transform_specialization(self, block_subset):
    for block in block_subset:
        for op in block.operations:
            if op.opname in ('simple_call', 'call_args'):
                callb = self.binding(op.args[0], extquery=True)
                if isinstance(callb, annmodel.SomePBC):
                    if len(callb.prebuiltinstances) == 1:
                        specialized_callb, specialcase = self.bookkeeper.query_spaceop_callable(op)
                        if specialcase or callb != specialized_callb:
                            if not specialcase:
                                op.args[0] = Constant(specialized_callb.prebuiltinstances.keys()[0])
                            else:
                                if op.opname != 'simple_call':
                                    assert 0, "not supported: call_args to a specialized function"
                                callable = callb.prebuiltinstances.keys()[0]
                                tag = getattr(callable, '_annspecialcase_', None)
                                if tag == 'specialize:memo':
                                    arglist_s = [self.binding(v) for v in op.args[1:]]
                                    memo_table = MemoTable(self.bookkeeper, 
                                                           callable, 
                                                           self.binding(op.result), 
                                                           arglist_s)
                                    op.opname = intern('call_memo')
                                    op.args[0] = Constant(memo_table)
                                else:
                                    op.opname = intern('call_specialcase')

default_extra_passes = [
    transform_specialization,
    transform_allocate,
    ]

def transform_graph(ann, extra_passes=default_extra_passes, block_subset=None):
    """Apply set of transformations available."""
    # WARNING: this produces incorrect results if the graph has been
    #          modified by t.simplify() after it had been annotated.
    if block_subset is None:
        block_subset = fully_annotated_blocks(ann)
    d = {}
    for block in block_subset:
        d[block] = True
    block_subset = d
    if ann.translator:
        checkgraphs(ann, block_subset)
    transform_dead_code(ann, block_subset)
    for pass_ in extra_passes:
        pass_(ann, block_subset)
    # do this last, after the previous transformations had a
    # chance to remove dependency on certain variables
    transform_dead_op_vars(ann, block_subset)
    if ann.translator:
        checkgraphs(ann, block_subset)
 
