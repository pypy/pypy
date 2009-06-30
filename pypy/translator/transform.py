"""Flow Graph Transformation

The difference between simplification and transformation is that
transformation is based on annotations; it runs after the annotator
completed.
"""

import types
from pypy.objspace.flow.model import SpaceOperation
from pypy.objspace.flow.model import Variable, Constant, Link
from pypy.objspace.flow.model import c_last_exception, checkgraph
from pypy.annotation import model as annmodel
from pypy.rlib.rstack import stack_check
from pypy.rpython.lltypesystem import lltype

def checkgraphs(self, blocks):
    seen = {}
    for block in blocks:
        graph = self.annotated[block]
        if graph not in seen:
            checkgraph(graph)
            seen[graph] = True

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

# lst += string[x:y]
# -->
# b = getslice(string, x, y)
# c = inplace_add(lst, b)
# -->
# c = extend_with_str_slice(lst, x, y, string)

def transform_extend_with_str_slice(self, block_subset):
    """Transforms lst += string[x:y] to extend_with_str_slice"""
    for block in block_subset:
        slice_sources = {}    # maps b to [string, slice] in the above notation
        for i in range(len(block.operations)):
            op = block.operations[i]
            if (op.opname == 'getslice' and
                self.gettype(op.args[0]) is str):
                slice_sources[op.result] = op.args
            elif (op.opname == 'inplace_add' and
                  op.args[1] in slice_sources and
                  self.gettype(op.args[0]) is list):
                v_string, v_x, v_y = slice_sources[op.args[1]]
                new_op = SpaceOperation('extend_with_str_slice',
                                        [op.args[0], v_x, v_y, v_string],
                                        op.result)
                block.operations[i] = new_op

# lst += char*count        [or count*char]
# -->
# b = mul(char, count)     [or count, char]
# c = inplace_add(lst, b)
# -->
# c = extend_with_char_count(lst, char, count)

def transform_extend_with_char_count(self, block_subset):
    """Transforms lst += char*count to extend_with_char_count"""
    for block in block_subset:
        mul_sources = {}    # maps b to (char, count) in the above notation
        for i in range(len(block.operations)):
            op = block.operations[i]
            if op.opname == 'mul':
                s0 = self.binding(op.args[0], None)
                s1 = self.binding(op.args[1], None)
                if (isinstance(s0, annmodel.SomeChar) and
                    isinstance(s1, annmodel.SomeInteger)):
                    mul_sources[op.result] = op.args[0], op.args[1]
                elif (isinstance(s1, annmodel.SomeChar) and
                      isinstance(s0, annmodel.SomeInteger)):
                    mul_sources[op.result] = op.args[1], op.args[0]
            elif (op.opname == 'inplace_add' and
                  op.args[1] in mul_sources and
                  self.gettype(op.args[0]) is list):
                v_char, v_count = mul_sources[op.args[1]]
                new_op = SpaceOperation('extend_with_char_count',
                                        [op.args[0], v_char, v_count],
                                        op.result)
                block.operations[i] = new_op


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
                elif block.exitswitch == c_last_exception:
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
    graph = self.annotated[block]
    msg = "Call to %r should have raised an exception" % (getattr(graph, 'func', None),)
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
    s_value = annmodel.SomeInstance(self.bookkeeper.getuniqueclassdef(Exception))
    self.setbinding(etype, s_type)
    self.setbinding(evalue, s_value)
    # make sure the bookkeeper knows about AssertionError
    self.bookkeeper.getuniqueclassdef(AssertionError)

def insert_stackcheck(ann):
    from pypy.tool.algo.graphlib import Edge, make_edge_dict, break_cycles
    edges = []
    graphs_to_patch = {}
    for callposition, (caller, callee) in ann.translator.callgraph.items():
        if getattr(getattr(callee, 'func', None), 'insert_stack_check_here', False):
            graphs_to_patch[callee] = True
            continue
        edge = Edge(caller, callee)
        edge.callposition = callposition
        edges.append(edge)

    for graph in graphs_to_patch:
        v = Variable()
        ann.setbinding(v, annmodel.SomeImpossibleValue())
        unwind_op = SpaceOperation('simple_call', [Constant(stack_check)], v)
        graph.startblock.operations.insert(0, unwind_op)

    edgedict = make_edge_dict(edges)
    for edge in break_cycles(edgedict, edgedict):
        caller = edge.source
        _, _, call_tag = edge.callposition
        if call_tag:
            caller_block, _ = call_tag
        else:
            ann.warning("cycle detected but no information on where to insert "
                        "stack_check()")
            continue
        # caller block found, insert stack_check()
        v = Variable()
        # push annotation on v
        ann.setbinding(v, annmodel.SomeImpossibleValue())
        unwind_op = SpaceOperation('simple_call', [Constant(stack_check)], v)
        caller_block.operations.insert(0, unwind_op)

def insert_ll_stackcheck(translator):
    from pypy.translator.backendopt.support import find_calls_from
    from pypy.rlib.rstack import stack_check
    from pypy.tool.algo.graphlib import Edge, make_edge_dict, break_cycles_v
    rtyper = translator.rtyper
    graph = rtyper.annotate_helper(stack_check, [])
    rtyper.specialize_more_blocks()
    stack_check_ptr = rtyper.getcallable(graph)
    stack_check_ptr_const = Constant(stack_check_ptr, lltype.typeOf(stack_check_ptr))
    edges = set()
    insert_in = set()
    for caller in translator.graphs:
        for block, callee in find_calls_from(translator, caller):
            if getattr(getattr(callee, 'func', None),
                       'insert_stack_check_here', False):
                insert_in.add(callee.startblock)
                continue
            if block is not caller.startblock:
                edges.add((caller.startblock, block))
            edges.add((block, callee.startblock))

    edgelist = [Edge(block1, block2) for (block1, block2) in edges]
    edgedict = make_edge_dict(edgelist)
    for block in break_cycles_v(edgedict, edgedict):
        insert_in.add(block)

    for block in insert_in:
        v = Variable()
        v.concretetype = lltype.Void
        unwind_op = SpaceOperation('direct_call', [stack_check_ptr_const], v)
        block.operations.insert(0, unwind_op)
    return len(insert_in)


default_extra_passes = [
    transform_allocate,
    transform_extend_with_str_slice,
    transform_extend_with_char_count,
    ]

def transform_graph(ann, extra_passes=None, block_subset=None):
    """Apply set of transformations available."""
    # WARNING: this produces incorrect results if the graph has been
    #          modified by t.simplify() after it had been annotated.
    if extra_passes is None:
        extra_passes = default_extra_passes
    if block_subset is None:
        block_subset = fully_annotated_blocks(ann)
    if not isinstance(block_subset, dict):
        block_subset = dict.fromkeys(block_subset)
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
 
