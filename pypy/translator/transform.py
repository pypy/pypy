"""Flow Graph Transformation

The difference between simplification and transformation is that
transformation is based on annotations; it runs after the annotator
completed.
"""

from __future__ import generators

import types
from pypy.objspace.flow.model import SpaceOperation
from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import last_exception
from pypy.translator.annrpython import CannotSimplify
from pypy.annotation import model as annmodel

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

def transform_allocate(self):
    """Transforms [a] * b to alloc_and_set(b, a) where b is int."""
    for block in fully_annotated_blocks(self):
        operations = block.operations[:]
        n_op = len(operations)
        for i in range(0, n_op-1):
            op1 = operations[i]
            op2 = operations[i+1]
            if (op1.opname == 'newlist' and
                len(op1.args) == 1 and
                op2.opname == 'mul' and
                op1.result is op2.args[0] and
                self.gettype(op2.args[1]) is int):
                new_op = SpaceOperation('alloc_and_set',
                                        (op2.args[1], op1.args[0]),
                                        op2.result)
                block.operations[i+1:i+2] = [new_op]

# a[b:c]
# -->
# d = newslice(b, c, None)
# e = getitem(a, d)
# -->
# e = getslice(a, b, c)

def transform_slice(self):
    """Transforms a[b:c] to getslice(a, b, c)."""
    for block in fully_annotated_blocks(self):
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

# a(*b)
# -->
# c = newtuple(*b)
# d = newdict()
# e = call(function a, c, d)
# -->
# e = simple_call(a, *b)

# ----------------------------------------------------------------------
# The 'call_args' operation is the strangest one.  The meaning of its
# arguments is as follows:
#
#      call_args(<callable>, <shape>, <arg0>, <arg1>, <arg2>...)
#
# The shape must be a constant object, which describes how the remaining
# arguments are regrouped.  The class pypy.interpreter.argument.Arguments
# has a method 'fromshape(shape, list-of-args)' that reconstructs a complete
# Arguments instance from this information.  Don't try to interpret the
# shape anywhere else, but for reference, it is a 3-tuple:
# (number-of-pos-arg, tuple-of-keyword-names, flag-presence-of-*-arg)
# ----------------------------------------------------------------------

## REMOVED: now FlowObjSpace produces 'call_args' operations only
##def transform_simple_call(self):
##    """Transforms call(a, (...), {}) to simple_call(a, ...)"""
##    for block in self.annotated:
##        known_vars = block.inputargs[:]
##        operations = []
##        for op in block.operations:
##            try:
##                if op.opname != 'call':
##                    raise CannotSimplify
##                varargs_cell = self.binding(op.args[1])
##                varkwds_cell = self.binding(op.args[2])
##                arg_cells = self.decode_simple_call(varargs_cell,
##                                                    varkwds_cell)
##                if arg_cells is None:
##                    raise CannotSimplify

##                args = [self.reverse_binding(known_vars, c) for c in arg_cells]
##                args.insert(0, op.args[0])
##                new_ops = [SpaceOperation('simple_call', args, op.result)]
                
##            except CannotSimplify:
##                new_ops = [op]

##            for op in new_ops:
##                operations.append(op)
##                known_vars.append(op.result)

##        block.operations = operations

def transform_dead_op_vars(self):
    # we redo the same simplification from simplify.py,
    # to kill dead (never-followed) links,
    # which can possibly remove more variables.
    from pypy.translator.simplify import transform_dead_op_vars_in_blocks
    transform_dead_op_vars_in_blocks(self.annotated)

# expands the += operation between lists into a basic block loop.
#    a = inplace_add(b, c)
# becomes the following graph:
#
#  clen = len(c)
#  growlist(b, clen)     # ensure there is enough space for clen new items
#        |
#        |  (pass all variables to next block, plus i=0)
#        V
#  ,--> z = lt(i, clen)
#  |    exitswitch(z):
#  |     |          |        False
#  |     | True     `------------------>  ...sequel...
#  |     V
#  |    x = getitem(c, i)
#  |    fastappend(b, x)
#  |    i1 = add(i, 1)
#  |     |
#  `-----'  (pass all variables, with i=i1)
#
##def transform_listextend(self):
##    allblocks = list(self.annotated)
##    for block in allblocks:
##        for j in range(len(block.operations)):
##            op = block.operations[j]
##            if op.opname != 'inplace_add':
##                continue
##            a = op.result
##            b, c = op.args
##            s_list = self.bindings.get(b)
##            if not isinstance(s_list, annmodel.SomeList):
##                continue

##            # new variables
##            clen  = Variable()
##            i     = Variable()
##            i1    = Variable()
##            z     = Variable()
##            x     = Variable()
##            dummy = Variable()
##            self.setbinding(clen,  annmodel.SomeInteger(nonneg=True))
##            self.setbinding(i,     annmodel.SomeInteger(nonneg=True))
##            self.setbinding(i1,    annmodel.SomeInteger(nonneg=True))
##            self.setbinding(z,     annmodel.SomeBool())
##            self.setbinding(x,     s_list.s_item)
##            self.setbinding(dummy, annmodel.SomeImpossibleValue())

##            sequel_operations = block.operations[j+1:]
##            sequel_exitswitch = block.exitswitch
##            sequel_exits      = block.exits

##            del block.operations[j:]
##            block.operations += [
##                SpaceOperation('len', [c], clen),
##                SpaceOperation('growlist', [b, clen], dummy),
##                ]
##            block.exitswitch = None
##            allvars = block.getvariables()

##            condition_block = Block(allvars+[i])
##            condition_block.operations += [
##                SpaceOperation('lt', [i, clen], z),
##                ]
##            condition_block.exitswitch = z

##            loopbody_block = Block(allvars+[i])
##            loopbody_block.operations += [
##                SpaceOperation('getitem', [c, i], x),
##                SpaceOperation('fastappend', [b, x], dummy),
##                SpaceOperation('add', [i, Constant(1)], i1),
##                ]

##            sequel_block = Block(allvars+[a])
##            sequel_block.operations = sequel_operations
##            sequel_block.exitswitch = sequel_exitswitch

##            # link the blocks together
##            block.recloseblock(
##                Link(allvars+[Constant(0)], condition_block),
##                )
##            condition_block.closeblock(
##                Link(allvars+[i],           loopbody_block,  exitcase=True),
##                Link(allvars+[b],           sequel_block,    exitcase=False),
##                )
##            loopbody_block.closeblock(
##                Link(allvars+[i1],          condition_block),
##                )
##            sequel_block.closeblock(*sequel_exits)

##            # now rename the variables -- so far all blocks use the
##            # same variables, which is forbidden
##            renamevariables(self, condition_block)
##            renamevariables(self, loopbody_block)
##            renamevariables(self, sequel_block)

##            allblocks.append(sequel_block)
##            break

##def renamevariables(self, block):
##    """Utility to rename the variables in a block to fresh variables.
##    The annotations are carried over from the old to the new vars."""
##    varmap = {}
##    block.inputargs = [varmap.setdefault(a, Variable())
##                       for a in block.inputargs]
##    operations = []
##    for op in block.operations:
##        result = varmap.setdefault(op.result, Variable())
##        args = [varmap.get(a, a) for a in op.args]
##        op = SpaceOperation(op.opname, args, result)
##        operations.append(op)
##    block.operations = operations
##    block.exitswitch = varmap.get(block.exitswitch, block.exitswitch)
##    exits = []
##    for exit in block.exits:
##        args = [varmap.get(a, a) for a in exit.args]
##        exits.append(Link(args, exit.target, exit.exitcase))
##    block.recloseblock(*exits)
##    # carry over the annotations
##    for a1, a2 in varmap.items():
##        if a1 in self.bindings:
##            self.setbinding(a2, self.bindings[a1])
##    self.annotated[block] = True

def transform_dead_code(self):
    """Remove dead code: these are the blocks that are not annotated at all
    because the annotation considered that no conditional jump could reach
    them."""
    for block in fully_annotated_blocks(self):
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

default_extra_passes = [
    transform_allocate,
    ]

def transform_graph(ann, extra_passes=default_extra_passes):
    """Apply set of transformations available."""
    # WARNING: this produces incorrect results if the graph has been
    #          modified by t.simplify() after it had been annotated.
    if ann.translator:
        ann.translator.checkgraphs()
    transform_dead_code(ann)
    for pass_ in extra_passes:
        pass_(ann)
    ##transform_listextend(ann)
    # do this last, after the previous transformations had a
    # chance to remove dependency on certain variables
    transform_dead_op_vars(ann)
    if ann.translator:
        ann.translator.checkgraphs()
